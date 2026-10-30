from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from PIL import Image
import io
import base64
from transformers import AutoProcessor, AutoModelForCausalLM, AutoConfig
import transformers.configuration_utils as config_utils
from transformers.dynamic_module_utils import get_imports
import torch
import logging
import os
from typing import List, Optional, Dict, Any, Union
from unittest.mock import patch
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress specific warnings that might interfere
warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub")

# --- Workaround for Florence-2 / TF-ID on systems without flash_attn ---
def _fixed_get_imports(filename: Union[str, os.PathLike]) -> List[str]:
    if not str(filename).endswith(("modeling_florence2.py", "modeling_phi.py")):
        return get_imports(filename)
    imports = get_imports(filename)
    if "flash_attn" in imports:
        logger.info("Removing 'flash_attn' from imports for compatibility.")
        imports.remove("flash_attn")
    return imports

# --- Pydantic Models for Request and Response ---
class ImageInput(BaseModel):
    image_base64: str

class Detection(BaseModel):
    bbox: List[float]  # [xmin, ymin, xmax, ymax]
    label: str

class DetectionResponse(BaseModel):
    detections: List[Detection]
    error: Optional[str] = None

# --- Global Variables / Model Loading ---
app = FastAPI(title="TF-ID Object Detection Worker (Generative)")
model: Optional[AutoModelForCausalLM] = None
processor: Optional[AutoProcessor] = None
device: str = "cuda" if torch.cuda.is_available() else "cpu"
TF_ID_MODEL_NAME = "yifeihu/TF-ID-base"

# --- Model Loading Function ---
def load_tf_id_generative_model():
    global model, processor
    if model is not None and processor is not None:
        logger.info("TF-ID Generative Model and processor already loaded.")
        return
    
    try:
        logger.info(f"Loading TF-ID Generative model ({TF_ID_MODEL_NAME}) and processor...")
        
        with patch("transformers.dynamic_module_utils.get_imports", _fixed_get_imports):
            # Store original logger state
            original_logger_level = config_utils.logger.level
            original_logger_disabled = getattr(config_utils.logger, 'disabled', False)
            
            try:
                # Suppress the config logger to avoid JSON serialization error
                config_utils.logger.disabled = True
                config_utils.logger.setLevel(logging.CRITICAL)
                
                # Load config first with trust_remote_code
                config = AutoConfig.from_pretrained(
                    TF_ID_MODEL_NAME,
                    trust_remote_code=True
                )
                
            finally:
                # Always restore logger state
                config_utils.logger.disabled = original_logger_disabled
                config_utils.logger.setLevel(original_logger_level)

            # Load processor
            processor = AutoProcessor.from_pretrained(
                TF_ID_MODEL_NAME,
                trust_remote_code=True
            )
            
            # Load model with the config
            model = AutoModelForCausalLM.from_pretrained(
                TF_ID_MODEL_NAME,
                config=config,
                trust_remote_code=True,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32
            )
        
        model.to(device)
        model.eval()
        logger.info(f"TF-ID Generative model ('{TF_ID_MODEL_NAME}') and processor loaded successfully on {device}.")
        
    except Exception as e:
        logger.error(f"Error loading TF-ID Generative model: {str(e)}", exc_info=True)
        model = None 
        processor = None
        raise

# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup (Generative TF-ID)...")
    try:
        load_tf_id_generative_model()
    except Exception as e:
        logger.error(f"Failed to load model during startup: {str(e)}")
        # Don't exit - let the health check handle retries

# --- API Endpoints ---
@app.get("/", summary="Root Endpoint")
async def root():
    return {"message": "TF-ID Object Detection Worker (Generative) is running."}

@app.get("/health", summary="Health Check")
async def health_check():
    if model is not None and processor is not None:
        return {
            "status": "healthy", 
            "model_loaded": True, 
            "model_name": TF_ID_MODEL_NAME, 
            "device": device
        }
    else:
        logger.warning("Health check: Model not loaded. Attempting to load now.")
        try:
            load_tf_id_generative_model()
            if model is not None and processor is not None:
                return {
                    "status": "healthy", 
                    "model_loaded": True, 
                    "model_name": TF_ID_MODEL_NAME, 
                    "device": device, 
                    "details": "Model loaded on health check."
                }
        except Exception as e:
            logger.error(f"Health check: Failed to load model on demand: {str(e)}")
        
        return {
            "status": "unhealthy", 
            "model_loaded": False, 
            "error": "Model or processor not loaded. Check logs."
        }

@app.post("/detect", response_model=DetectionResponse, summary="Detect Objects (Generative)")
async def detect_objects_generative(image_input: ImageInput):
    if model is None or processor is None:
        logger.error("Detection endpoint called but generative model/processor not loaded.")
        raise HTTPException(
            status_code=503, 
            detail="Model not available. Please try again later or check service health."
        )

    try:
        logger.info("Received generative detection request.")
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_input.image_base64)
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            logger.error(f"Error decoding base64 image: {str(e)}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid base64 image data: {str(e)}"
            )

        logger.info(f"Image decoded (size: {pil_image.size}). Processing with Generative TF-ID model on {device}...")
        
        prompt = "<OD>"  # Object Detection prompt for TF-ID

        inputs = processor(text=prompt, images=pil_image, return_tensors="pt")
        
        # Move tensors to device and handle dtype for pixel_values
        for key, tensor_val in inputs.items():
            if torch.is_tensor(tensor_val):
                if key == 'pixel_values' and device == 'cuda' and model.dtype == torch.float16:
                    inputs[key] = tensor_val.to(device).half()
                    logger.debug(f"Casting pixel_values to half on CUDA. Original dtype: {tensor_val.dtype}, New dtype: {inputs[key].dtype}")
                else:
                    inputs[key] = tensor_val.to(device)

        # Model generation with proper error handling
        with torch.no_grad():
            generated_ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024, 
                do_sample=False,
                num_beams=3,
                pad_token_id=processor.tokenizer.pad_token_id,
                eos_token_id=processor.tokenizer.eos_token_id
            )
        
        # Batch decode and post-process
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        logger.debug(f"Generated text from model: {generated_text}")

        parsed_answer = processor.post_process_generation(
            generated_text, 
            task=prompt, 
            image_size=(pil_image.width, pil_image.height)
        )
        logger.debug(f"Parsed answer from post_process_generation: {parsed_answer}")
        
        detections_list: List[Detection] = []
        
        if parsed_answer and prompt in parsed_answer and isinstance(parsed_answer[prompt], dict):
            detection_results = parsed_answer[prompt]
            bboxes = detection_results.get('bboxes', [])
            labels = detection_results.get('labels', [])
            
            page_width, page_height = pil_image.size

            logger.info(f"TF-ID (generative) initially found {len(bboxes)} objects based on parsed output.")
            
            for i, (box, label_str) in enumerate(zip(bboxes, labels)):
                bbox_coords = [round(c, 2) for c in box] 
                current_label = label_str.lower()
                logger.debug(f"  Raw detected object {i}: '{current_label}' with box {bbox_coords}")

                # Filter by label
                relevant_labels = ['table', 'tabular', 'figure']
                if current_label not in relevant_labels:
                    logger.debug(f"    Ignoring object '{current_label}' (not in {relevant_labels}).")
                    continue

                # Basic validation: reject very small boxes relative to page size
                min_rel_width = 0.05
                min_rel_height = 0.03
                
                box_width = bbox_coords[2] - bbox_coords[0]
                box_height = bbox_coords[3] - bbox_coords[1]

                if not (box_width > min_rel_width * page_width and box_height > min_rel_height * page_height):
                    logger.debug(f"    Rejected '{current_label}': too small (width={box_width:.1f} vs min_req_width={min_rel_width*page_width:.1f}, height={box_height:.1f} vs min_req_height={min_rel_height*page_height:.1f})")
                    continue
                
                logger.info(f"    Keeping filtered object: '{current_label}' at {bbox_coords}")
                detections_list.append(Detection(bbox=bbox_coords, label=current_label))
        else:
            logger.warning(f"TF-ID (generative) returned an unexpected result format or no '{prompt}' key. Parsed: {parsed_answer}")

        logger.info(f"Found {len(detections_list)} relevant, filtered object(s).")
        return DetectionResponse(detections=detections_list, error=None)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during generative detection: {str(e)}", exc_info=True)
        return DetectionResponse(detections=[], error=f"An unexpected error occurred: {str(e)}")

# Run command for local testing:
# uvicorn app.main:app --reload --port 8000

if __name__ == "__main__":
    import uvicorn
    # For RunPod Pod deployment, we need to listen on all interfaces
    # RunPod will expose this via port mapping
    uvicorn.run(app, host="0.0.0.0", port=8000)