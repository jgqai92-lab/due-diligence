"""Integration tests for IST Frameworks Reference Panel.

Tests cover:
- GET /api/frameworks/ist         -- list all frameworks (summaries)
- GET /api/frameworks/ist/{name}  -- single framework detail
- 404 for unknown framework name
- Error format compliance (INV-BE-02)
- content / scoringSchema presence in detail but absence in list
"""


# All 7 expected framework names in definition order.
EXPECTED_NAMES = [
    "scarcity_scoring",
    "bottleneck_cascade",
    "demand_modeling",
    "external_validation",
    "dialectic_scrutiny",
    "effects_mapping",
    "stress_testing",
]

# Fields that MUST appear in list summaries.
SUMMARY_FIELDS = {"name", "displayName", "description", "category"}

# Additional fields that MUST appear in detail responses.
DETAIL_EXTRA_FIELDS = {"content", "scoringSchema"}


# ── GET /api/frameworks/ist ──────────────────────────────────────────────────


class TestListISTFrameworks:
    """Tests for GET /api/frameworks/ist."""

    def test_list_returns_200(self, client):
        resp = client.get("/api/frameworks/ist")
        assert resp.status_code == 200

    def test_list_returns_7_frameworks(self, client):
        data = client.get("/api/frameworks/ist").json()
        assert data["total"] == 7
        assert len(data["frameworks"]) == 7

    def test_list_returns_correct_names(self, client):
        data = client.get("/api/frameworks/ist").json()
        names = [fw["name"] for fw in data["frameworks"]]
        assert names == EXPECTED_NAMES

    def test_list_summary_has_required_fields(self, client):
        data = client.get("/api/frameworks/ist").json()
        for fw in data["frameworks"]:
            for field in SUMMARY_FIELDS:
                assert field in fw, f"Missing field '{field}' in framework '{fw.get('name')}'"

    def test_list_summary_excludes_content(self, client):
        """List endpoint must NOT include the heavy content or scoringSchema fields."""
        data = client.get("/api/frameworks/ist").json()
        for fw in data["frameworks"]:
            assert "content" not in fw, (
                f"Framework '{fw['name']}' should not have 'content' in list summary"
            )
            assert "scoringSchema" not in fw, (
                f"Framework '{fw['name']}' should not have 'scoringSchema' in list summary"
            )

    def test_list_categories_are_valid(self, client):
        valid_categories = {"equity_analysis", "thematic_analysis", "quality_assurance"}
        data = client.get("/api/frameworks/ist").json()
        for fw in data["frameworks"]:
            assert fw["category"] in valid_categories, (
                f"Invalid category '{fw['category']}' for '{fw['name']}'"
            )


# ── GET /api/frameworks/ist/{name} ───────────────────────────────────────────


class TestGetISTFrameworkDetail:
    """Tests for GET /api/frameworks/ist/{name}."""

    def test_detail_returns_200_for_each_framework(self, client):
        """Every known framework name returns 200."""
        for name in EXPECTED_NAMES:
            resp = client.get(f"/api/frameworks/ist/{name}")
            assert resp.status_code == 200, f"Failed for framework '{name}'"

    def test_detail_includes_content(self, client):
        """Detail response must include the full markdown content."""
        for name in EXPECTED_NAMES:
            data = client.get(f"/api/frameworks/ist/{name}").json()
            assert "content" in data, f"Missing 'content' for '{name}'"
            assert isinstance(data["content"], str)
            assert len(data["content"]) > 50, (
                f"Content too short for '{name}' -- likely empty"
            )

    def test_detail_includes_scoring_schema(self, client):
        """Detail response must include scoringSchema (may be None)."""
        for name in EXPECTED_NAMES:
            data = client.get(f"/api/frameworks/ist/{name}").json()
            assert "scoringSchema" in data, f"Missing 'scoringSchema' for '{name}'"

    def test_scarcity_scoring_has_non_null_schema(self, client):
        """scarcity_scoring is the only framework with a populated scoringSchema."""
        data = client.get("/api/frameworks/ist/scarcity_scoring").json()
        schema = data["scoringSchema"]
        assert schema is not None
        assert "dimensions" in schema
        assert len(schema["dimensions"]) == 5
        assert schema["scale"]["min"] == 1
        assert schema["scale"]["max"] == 5
        assert schema["tierThresholds"]["tier1"] == 4.0
        assert schema["tierThresholds"]["tier2"] == 3.0

    def test_non_scarcity_frameworks_have_null_schema(self, client):
        """All frameworks except scarcity_scoring have scoringSchema=None."""
        for name in EXPECTED_NAMES:
            if name == "scarcity_scoring":
                continue
            data = client.get(f"/api/frameworks/ist/{name}").json()
            assert data["scoringSchema"] is None, (
                f"Expected null scoringSchema for '{name}'"
            )

    def test_detail_includes_summary_fields(self, client):
        """Detail response also includes the summary fields."""
        data = client.get("/api/frameworks/ist/scarcity_scoring").json()
        for field in SUMMARY_FIELDS:
            assert field in data


# ── 404 and error format ─────────────────────────────────────────────────────


class TestFrameworkErrors:
    """Test error handling and INV-BE-02 error format compliance."""

    def test_unknown_framework_returns_404(self, client):
        resp = client.get("/api/frameworks/ist/nonexistent_framework")
        assert resp.status_code == 404

    def test_404_error_format_inv_be_02(self, client):
        """Error body must follow INV-BE-02: {"error": {"code": ..., "message": ...}}."""
        resp = client.get("/api/frameworks/ist/nonexistent_framework")
        detail = resp.json()["detail"]
        assert "error" in detail
        assert "code" in detail["error"]
        assert "message" in detail["error"]
        assert detail["error"]["code"] == "FRAMEWORK_NOT_FOUND"

    def test_404_message_includes_valid_names(self, client):
        """Error message should list valid framework names for discoverability."""
        resp = client.get("/api/frameworks/ist/bogus")
        msg = resp.json()["detail"]["error"]["message"]
        for name in EXPECTED_NAMES:
            assert name in msg, f"Error message should mention valid name '{name}'"
