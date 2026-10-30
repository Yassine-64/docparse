class DocparseError(Exception):
    """Base class for every error raised by docparse."""


class UnsupportedFormat(DocparseError):
    def __init__(self, suffix: str) -> None:
        super().__init__(f"unsupported file format: {suffix or '<none>'}")
        self.suffix = suffix


class EncryptedDocument(DocparseError):
    pass


class ExtractionFailed(DocparseError):
    pass


class QualityRejected(DocparseError):
    def __init__(self, report_markdown: str) -> None:
        super().__init__("document rejected by quality gate")
        self.report_markdown = report_markdown
