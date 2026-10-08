"""Domain errors raised by the RAG module."""


class DocumentTypeNotFoundError(Exception):
    """A document type with the requested id does not exist."""


class DocumentTypeNameTakenError(Exception):
    """Another document type already uses the requested name."""