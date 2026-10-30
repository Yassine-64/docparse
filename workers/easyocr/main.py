from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from PIL import Image
import io
import base64
import easyocr
import torch # To check for CUDA
import logging
from typing import List, Optional, Tuple 
import warnings # Added

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress common warnings if they become too noisy (optional)
# warnings.filterwarnings("ignore", category=UserWarning, module="torch.utils.data.dataloader")

# --- Pydantic Models for Request and Response ---
class ImageInput(BaseModel):
    image_base64: str

class OCRResultDetail(BaseModel):
    bbox: List[List[int]] 
    text: str
    confidence: float

class OCRResponse(BaseModel):
    results: List[OCRResultDetail] 
    full_text: str 
    error: Optional[str] = None

# --- Global Variables / Model Loading ---
app = FastAPI(title="EasyOCR Worker")
easyocr_reader: Optional[easyocr.Reader] = None
device: str = "cuda" if torch.cuda.is_available() else "cpu"
# Define languages, can be made configurable if needed
LANGUAGES = ['en', 'fr'] 

# --- Model Loading Function (EasyOCR Reader) ---
def load_easyocr_reader():
    global easyocr_reader
    if easyocr_reader is not None:
        logger.info("EasyOCR Reader already loaded.")
        return
    try:
        logger.info(f"Loading EasyOCR Reader for languages {LANGUAGES} on device: {device}...")
        easyocr_reader = easyocr.Reader(LANGUAGES, gpu=(device == 'cuda')) 
        logger.info(f"EasyOCR Reader for {LANGUAGES} loaded successfully on {device}.")
    except Exception as e:
        logger.error(f"Error loading EasyOCR Reader: {str(e)}", exc_info=True)
        easyocr_reader = None 
        raise # Re-raise critical failure

# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup (EasyOCR Worker)...")
    try:
        load_easyocr_reader()
    except Exception as e:
        logger.error(f"Failed to load EasyOCR reader during startup: {str(e)}")
        # App will start, but /health will be unhealthy.

# --- API Endpoints ---
@app.get("/", summary="Root Endpoint")
async def root():
    return {"message": "EasyOCR Worker is running."}

@app.get("/health", summary="Health Check")
async def health_check():
    if easyocr_reader is not None:
        return {
            "status": "healthy", 
            "easyocr_reader_loaded": True, 
            "languages": LANGUAGES,
            "device_preference": device
        }
    else:
        logger.warning("Health check: EasyOCR Reader not loaded. Attempting to load now as a fallback.")
        try:
            load_easyocr_reader() # Try to load again
            if easyocr_reader is not None:
                return {
                    "status": "healthy", 
                    "easyocr_reader_loaded": True, 
                    "languages": LANGUAGES,
                    "device_preference": device, 
                    "details": "Reader loaded on health check retry."
                }
        except Exception as e:
            logger.error(f"Health check: Failed to load EasyOCR Reader on demand during retry: {str(e)}")
        
        return {
            "status": "unhealthy", 
            "easyocr_reader_loaded": False, 
            "error": "EasyOCR Reader not loaded. Check startup logs and previous health check attempts."
        }

@app.post("/ocr", response_model=OCRResponse, summary="Perform OCR on Image")
async def perform_ocr(image_input: ImageInput):
    if easyocr_reader is None:
        logger.error("OCR endpoint called but EasyOCR Reader not loaded.")
        raise HTTPException(
            status_code=503, 
            detail="EasyOCR Reader not available. Please try again later or check service health."
        )

    try:
        logger.info("Received OCR request.")
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_input.image_base64)
            # EasyOCR can take image bytes directly
        except Exception as e:
            logger.error(f"Error decoding base64 image: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")

        logger.info(f"Image decoded. Performing OCR with EasyOCR...")
        
        # Perform OCR
        # detail=1 gives bbox, text, and confidence. detail=0 gives only text.
        ocr_results_raw = easyocr_reader.readtext(image_bytes, detail=1, paragraph=False)
        # paragraph=False gives line-by-line or word-by-word based on the model.
        # paragraph=True tries to join results into paragraphs.
        # For more structured data, paragraph=False is often better.

        processed_results: List[OCRResultDetail] = []
        full_text_lines: List[str] = []

        for (bbox_points, text, confidence) in ocr_results_raw:
            processed_bbox = [[int(point[0]), int(point[1])] for point in bbox_points]
            processed_results.append(OCRResultDetail(
                bbox=processed_bbox,
                text=text,
                confidence=float(confidence)
            ))
            full_text_lines.append(text)
            logger.debug(f"OCR'd text: \\\"{text}\\\" with confidence {confidence:.4f} at bbox {processed_bbox}")
        
        concatenated_text = "\\n".join(full_text_lines)

        logger.info(f"OCR complete. Found {len(processed_results)} text blocks.")
        return OCRResponse(results=processed_results, full_text=concatenated_text, error=None)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during OCR: {str(e)}", exc_info=True)
        return OCRResponse(results=[], full_text="", error=f"An unexpected error occurred: {str(e)}")

# For direct execution (e.g., `python app/main.py`), not typically used by Docker CMD.
# if __name__ == "__main__":
#     import uvicorn
#     # Host 0.0.0.0 to be reachable within Docker and for RunPod Pod port mapping
#     uvicorn.run(app, host="0.0.0.0", port=8000) 