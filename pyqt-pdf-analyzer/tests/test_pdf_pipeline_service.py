import os
import fitz
import pytest
from services.PDFPipelineService import PDFPipelineService
from core.annotation_system import AnnotationManager, AnnotationType, Annotation
from models.DocumentInfo import DocumentInfo
from models.AnnotationSummary import AnnotationSummary

class DummyPage:
    def get_text(self):
        return "Sample text"

class DummyDoc:
    def __init__(self):
        self.metadata = {"title": "T", "author": "A", "subject": "S"}
        self.name = "dummy.pdf"
    def __len__(self):
        return 1
    def load_page(self, num):
        return DummyPage()

def test_open_document_success(tmp_path):
    file_path = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(file_path))
    doc.close()

    service = PDFPipelineService(AnnotationManager())
    assert service.open_document(str(file_path)) is True
    assert service.document is not None
    service.document.close()

def test_open_document_failure(monkeypatch):
    monkeypatch.setattr(fitz, "open", lambda path: (_ for _ in ()).throw(RuntimeError("fail")))
    service = PDFPipelineService(AnnotationManager())
    assert service.open_document("no.pdf") is False

def test_get_info_with_dummy(monkeypatch):
    service = PDFPipelineService(AnnotationManager())
    service.document = DummyDoc()
    monkeypatch.setattr("core.metadata_builder.PageMetadataBuilder.build",
                        lambda self, doc, num: {"dummy": True})
    info = service.get_info()
    assert isinstance(info, DocumentInfo)
    assert info.page_count == 1
    assert info.title == "T"
    assert info.author == "A"
    assert info.subject == "S"
    assert 0 in info.page_metadata

def test_load_and_extract_text(monkeypatch):
    service = PDFPipelineService(AnnotationManager())
    service.document = DummyDoc()
    assert service.load_page(0) is True
    text = service.extract_text()
    assert text == "Sample text"

def test_find_annotations_summary(monkeypatch):
    # Prepare annotation_manager to return mixed annotations
    am = AnnotationManager()
    dummy_ann_kw = Annotation("kw", AnnotationType.KEYWORD, "cat", "#ff0000", {})
    dummy_ann_url = Annotation("url", AnnotationType.URL_VALIDATION, "cat", "#00ff00", {})
    monkeypatch.setattr(am, "find_all_annotations_in_text",
                        lambda text: [dummy_ann_kw, dummy_ann_url, dummy_ann_kw])
    service = PDFPipelineService(am)
    service.document = DummyDoc()
    service.page_metadata = {0: None}
    service.load_page(0)
    summary = service.find_annotations()
    assert isinstance(summary, AnnotationSummary)
    assert summary.total == 3
    assert summary.keywords == 2
    assert summary.urls == 1
