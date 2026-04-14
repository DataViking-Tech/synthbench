"""Schema validation for the novel_products contamination-free suite."""

from __future__ import annotations

import json

import pytest

from synthbench.suites import SUITE_DIR


SUITE_PATH = SUITE_DIR / "novel_products.json"

REQUIRED_ITEM_FIELDS = {
    "key",
    "category",
    "product_name",
    "source_products",
    "features",
    "description",
    "prompt",
    "options",
}

REQUIRED_FEATURE_FIELDS = {"text", "source"}


@pytest.fixture(scope="module")
def suite():
    with open(SUITE_PATH) as f:
        return json.load(f)


class TestNovelProductsSuite:
    def test_file_exists(self):
        assert SUITE_PATH.exists(), f"Missing suite file: {SUITE_PATH}"

    def test_suite_metadata(self, suite):
        assert suite["suite"] == "novel_products"
        assert suite["version"]
        assert suite["description"]
        assert suite["n_items"] == len(suite["items"])
        assert suite["n_items"] >= 30

    def test_no_human_distribution_field(self, suite):
        for item in suite["items"]:
            assert "human_distribution" not in item, (
                f"{item['key']}: novel products must not ship ground-truth "
                f"distributions — they are fictional and uncontaminated by design."
            )

    def test_item_keys_unique(self, suite):
        keys = [item["key"] for item in suite["items"]]
        assert len(keys) == len(set(keys)), "Duplicate keys in novel_products suite"

    def test_item_required_fields(self, suite):
        for item in suite["items"]:
            missing = REQUIRED_ITEM_FIELDS - set(item.keys())
            assert not missing, f"{item['key']}: missing fields {missing}"

    def test_source_products_combine_multiple(self, suite):
        for item in suite["items"]:
            sources = item["source_products"]
            assert isinstance(sources, list)
            assert len(sources) >= 2, (
                f"{item['key']}: a synthetic product must combine features from "
                f"at least 2 real source products, got {len(sources)}"
            )
            assert len(set(sources)) == len(sources), (
                f"{item['key']}: duplicate source_products"
            )

    def test_features_attributed_to_sources(self, suite):
        for item in suite["items"]:
            features = item["features"]
            assert isinstance(features, list)
            assert len(features) >= 2, (
                f"{item['key']}: expected >=2 features, got {len(features)}"
            )
            declared_sources = set(item["source_products"])
            for feat in features:
                missing = REQUIRED_FEATURE_FIELDS - set(feat.keys())
                assert not missing, f"{item['key']}: feature missing fields {missing}"
                assert feat["source"] in declared_sources, (
                    f"{item['key']}: feature source {feat['source']!r} not in "
                    f"declared source_products"
                )

    def test_every_source_contributes_a_feature(self, suite):
        for item in suite["items"]:
            feature_sources = {f["source"] for f in item["features"]}
            for src in item["source_products"]:
                assert src in feature_sources, (
                    f"{item['key']}: declared source {src!r} contributes no feature"
                )

    def test_options_are_multiple_choice(self, suite):
        for item in suite["items"]:
            options = item["options"]
            assert isinstance(options, list)
            assert len(options) >= 2, (
                f"{item['key']}: need >= 2 options, got {len(options)}"
            )
            assert len(set(options)) == len(options), (
                f"{item['key']}: duplicate option strings"
            )

    def test_product_name_fictional(self, suite):
        """Product names must not collide with any declared source product."""
        for item in suite["items"]:
            name = item["product_name"]
            for source in item["source_products"]:
                assert name != source, (
                    f"{item['key']}: product_name {name!r} collides with a "
                    f"source product — must be fictional"
                )

    def test_description_mentions_product_name(self, suite):
        for item in suite["items"]:
            assert item["product_name"] in item["description"], (
                f"{item['key']}: description should reference product_name"
            )

    def test_prompt_and_description_non_empty(self, suite):
        for item in suite["items"]:
            assert item["prompt"].strip()
            assert item["description"].strip()
