from __future__ import annotations

import respx
from httpx import Response

from ebrag.parsers.grobid_parser import GrobidParser
from ebrag.schemas.paper import SourceDocument

TEI_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc><titleStmt><title>Compound X and IL-6</title></titleStmt></fileDesc>
    <profileDesc><abstract><p>Compound X reduced IL-6 in mice.</p></abstract></profileDesc>
  </teiHeader>
  <text>
    <body>
      <div><head>Methods</head><p>Mice received Compound X.</p></div>
      <div><head>Results</head><p>IL-6 decreased after treatment.</p></div>
      <figure><figDesc>IL-6 bar plot.</figDesc></figure>
    </body>
    <back>
      <listBibl><biblStruct><monogr><title>Reference A</title></monogr></biblStruct></listBibl>
    </back>
  </text>
</TEI>
"""


@respx.mock
def test_grobid_parser_calls_api_and_extracts_tei() -> None:
    route = respx.post("http://grobid.test/api/processFulltextDocument").mock(
        return_value=Response(200, content=TEI_XML)
    )
    source = SourceDocument(
        document_id="doc-pdf",
        paper_id="P00000001",
        source_format="PDF",
        uri="memory://paper.pdf",
        filename="paper.pdf",
        content_bytes=b"%PDF test",
    )

    parsed = GrobidParser(grobid_url="http://grobid.test").parse(source)

    assert route.called
    assert parsed.parse_status == "parsed"
    assert parsed.parser_name == "grobid"
    assert parsed.title == "Compound X and IL-6"
    assert any(chunk.section == "Results" for chunk in parsed.chunks)
    assert parsed.references == ["Reference A"]


@respx.mock
def test_grobid_parser_returns_failed_document_on_error() -> None:
    respx.post("http://grobid.test/api/processFulltextDocument").mock(
        return_value=Response(500, text="boom")
    )
    source = SourceDocument(
        document_id="doc-pdf",
        paper_id="P00000001",
        source_format="PDF",
        uri="memory://paper.pdf",
        filename="paper.pdf",
        content_bytes=b"%PDF test",
    )

    parsed = GrobidParser(grobid_url="http://grobid.test").parse(source)

    assert parsed.parse_status == "failed"
    assert parsed.error is not None
