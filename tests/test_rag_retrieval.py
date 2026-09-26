import json
import unittest
from pathlib import Path

from rag.retrieval import build_corpus, retrieve


class RagRetrievalTest(unittest.TestCase):
    def setUp(self):
        self.corpus = build_corpus(
            [
                {"source": "ARCHITECTURE.md", "section": "Versioned publication", "text": "The verified release is reopened read-only before compact public aggregates are built."},
                {"source": "EVALUATION.md", "section": "Stage 4 static product", "text": "The dashboard distinguishes prediction observations from actual arrivals and shows coverage caveats."},
            ]
        )

    def test_known_question_returns_source_and_section(self):
        result = retrieve("How is a release published?", self.corpus)
        self.assertEqual(result["status"], "supported")
        self.assertEqual(result["citations"], [{"source": "ARCHITECTURE.md", "section": "Versioned publication"}])

    def test_unsupported_question_is_explicitly_insufficient(self):
        result = retrieve("What is the weather impact on delays?", self.corpus)
        self.assertEqual(result, {"status": "insufficient", "citations": [], "passages": []})

    def test_sanitizer_rejects_secrets_and_private_paths(self):
        with self.assertRaises(ValueError):
            build_corpus([{"source": "bad.md", "section": "x", "text": "GEMINI_API_KEY=secret"}])
        with self.assertRaises(ValueError):
            build_corpus([{"source": "bad.md", "section": "x", "text": "/home/rama/private/release.duckdb"}])
        with self.assertRaises(ValueError):
            build_corpus([{"source": "/etc/hidden.md", "section": "x", "text": "approved prose"}])
        with self.assertRaises(ValueError):
            build_corpus([{"source": "ARCHITECTURE.md", "section": "secret", "text": "approved prose"}])
        with self.assertRaises(ValueError):
            build_corpus([{"source": "ARCHITECTURE.md", "section": "private/path", "text": "approved prose"}])
        with self.assertRaises(ValueError):
            retrieve("secret", [{"source": "ARCHITECTURE.md", "section": "Versioned publication", "text": "/etc/secret"}])

    def test_approved_evaluation_fixture(self):
        root = Path(__file__).parents[1]
        corpus = build_corpus(json.loads((root / "rag" / "corpus.json").read_text()))
        for case in json.loads((root / "tests" / "fixtures" / "rag_eval.json").read_text()):
            result = retrieve(case["question"], corpus)
            if case.get("expected_status"):
                self.assertEqual(result["status"], case["expected_status"])
            else:
                self.assertEqual(result["citations"][0]["source"], case["expected_source"])
                self.assertEqual(result["citations"][0]["section"], case["expected_section"])


if __name__ == "__main__":
    unittest.main()
