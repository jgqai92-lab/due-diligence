# Testing Strategy

## Testing Philosophy

"Trust, but Verify (with Math)" applies to our own code. Forensic calculations must be provably correct — a wrong M-Score could drive a bad investment decision. Citation integrity is non-negotiable. The UI must meet commercial-grade standards under test.

## Testing Pyramid

```
        /\
       /E2\         End-to-End: 10% (Playwright)
      /____\
     /      \
    /Integr- \      Integration: 30% (API + Component)
   /  ation   \
  /____________\
 /              \
/     Unit       \  Unit: 60% (Forensic calcs, utils)
/________________\
```

## Coverage Targets

| Layer | Target | Notes |
|-------|--------|-------|
| **Forensic Calculations** | **100%** | Every formula, every component, every boundary |
| **Citation Logic** | **100%** | Every value must trace to source |
| **Backend API** | 85%+ | All endpoints, error cases, caching |
| **Frontend Components** | 75%+ | All states, interactions, accessibility |
| **E2E Critical Paths** | 100% of defined paths | Analyze ticker, view report, manage portfolio |

## Tools

| Tool | Purpose |
|------|---------|
| **pytest** | Python backend unit + integration tests |
| **pytest-cov** | Coverage reporting |
| **Vitest** | Next.js frontend unit tests |
| **React Testing Library** | Component interaction tests |
| **Playwright** | End-to-end browser tests |
| **jest-axe** | Accessibility violation detection |
| **httpx** | Async HTTP client for API integration tests |

---

## Backend Testing (Python / FastAPI)

### Unit Tests — Forensic Calculations (HIGHEST PRIORITY)

**Beneish M-Score:**
```python
class TestBeneishMScore:
    def test_dsri_calculation(self, sample_financials):
        """DSRI = (Receivables_t/Revenue_t) / (Receivables_t-1/Revenue_t-1)"""
        result = calculate_dsri(sample_financials)
        assert result.value == pytest.approx(1.124, abs=0.001)
        assert result.citation.line_items == ["Net Receivables", "Total Revenue"]

    def test_composite_m_score(self, sample_financials):
        """M = -4.84 + 0.920*DSRI + 0.528*GMI + ... """
        result = calculate_m_score(sample_financials)
        assert result.composite == pytest.approx(-2.45, abs=0.01)
        assert result.interpretation == "UNLIKELY_MANIPULATOR"

    def test_m_score_boundary_at_threshold(self):
        """Exactly at -1.78 should be GREY_ZONE"""
        assert classify_m_score(-1.78) == "GREY_ZONE"
        assert classify_m_score(-1.77) == "LIKELY_MANIPULATOR"
        assert classify_m_score(-1.79) == "GREY_ZONE"
        assert classify_m_score(-2.22) == "GREY_ZONE"
        assert classify_m_score(-2.23) == "UNLIKELY_MANIPULATOR"

    def test_missing_data_returns_data_not_available(self):
        """Missing fields must produce 'Data Not Available', not NaN or None"""
        incomplete = {**sample_financials, "net_receivables": None}
        result = calculate_dsri(incomplete)
        assert result.value is None
        assert result.status == "DATA_NOT_AVAILABLE"
        assert "Net Receivables" in result.reason

    # Tests for all 8 components: GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA
```

**Altman Z-Score:**
```python
class TestAltmanZScore:
    def test_standard_z_score(self, sample_financials):
        result = calculate_z_score(sample_financials, variant="standard")
        assert result.zone == "SAFE"
        assert result.score > 2.99

    def test_saas_modified_variant(self, sample_financials):
        result = calculate_z_score(sample_financials, variant="saas_modified")
        assert result.disclaimer is not None
        assert "not academically validated" in result.disclaimer

    def test_zone_boundaries(self):
        assert classify_z_score(3.00) == "SAFE"
        assert classify_z_score(2.99) == "GREY"
        assert classify_z_score(1.81) == "GREY"
        assert classify_z_score(1.80) == "DISTRESS"
```

**SaaS Metrics:**
```python
class TestSaaSMetrics:
    def test_rule_of_40_passing(self):
        result = calculate_rule_of_40(revenue_growth=25.0, fcf_margin=20.0)
        assert result.score == 45.0
        assert result.interpretation == "PASSING"

    def test_magic_number_with_zero_sm_spend(self):
        """Zero S&M spend should return Data Not Available, not division by zero"""
        result = calculate_magic_number(net_new_arr=1000000, sm_spend=0)
        assert result.value is None
        assert result.status == "DATA_NOT_AVAILABLE"
```

### Unit Tests — Citation Integrity

```python
class TestCitationIntegrity:
    def test_every_metric_has_citation(self, full_analysis):
        """Every calculated value must have a citation object"""
        for component in full_analysis.m_score.components:
            assert component.citation is not None
            assert component.citation.source != ""
            assert component.citation.line_items is not None
            assert len(component.citation.line_items) > 0

    def test_citation_matches_source_data(self, full_analysis, raw_data):
        """Cited raw values must match what yfinance returned"""
        for citation in full_analysis.all_citations():
            if citation.raw_value is not None:
                assert citation.raw_value == raw_data[citation.line_item][citation.period]

    def test_missing_data_shows_data_not_available(self):
        """Null fields must produce 'Data Not Available' string, never NaN"""
        result = generate_report_with_missing_data()
        assert "Data Not Available" in result.llm_report
        assert "NaN" not in result.llm_report
        assert "null" not in result.llm_report
        assert "undefined" not in result.llm_report
```

### Integration Tests — yfinance + Caching

```python
class TestYFinanceIntegration:
    def test_fetch_valid_ticker(self):
        data = fetch_financial_data("AAPL")
        assert data.financials is not None
        assert data.balance_sheet is not None
        assert data.cashflow is not None

    def test_cache_hit_within_24h(self, db_session):
        """Second fetch should use SQLite cache"""
        fetch_financial_data("AAPL")
        result = fetch_financial_data("AAPL")
        assert result.cache_hit is True

    def test_cache_miss_after_expiry(self, db_session, frozen_time):
        fetch_financial_data("AAPL")
        frozen_time.tick(timedelta(hours=25))
        result = fetch_financial_data("AAPL")
        assert result.cache_hit is False

    def test_unknown_ticker_returns_not_found(self):
        with pytest.raises(TickerNotFoundError):
            fetch_financial_data("ZZZZZ")

    def test_manual_refresh_bypasses_cache(self, db_session):
        fetch_financial_data("AAPL")
        result = fetch_financial_data("AAPL", force_refresh=True)
        assert result.cache_hit is False
```

### Integration Tests — API Endpoints

```python
class TestAnalyzeEndpoint:
    async def test_analyze_valid_ticker(self, client):
        response = await client.get("/api/analyze/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert "beneishMScore" in data["forensicMetrics"]
        assert "bearCase" in data["report"]["markdown"].lower()

    async def test_analyze_invalid_ticker_format(self, client):
        response = await client.get("/api/analyze/123INVALID")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "TICKER_INVALID"

    async def test_analyze_unknown_ticker(self, client):
        response = await client.get("/api/analyze/ZZZZZ")
        assert response.status_code == 404
```

### Hallucination Prevention Tests

```python
class TestHallucinationPrevention:
    def test_report_contains_no_fabricated_numbers(self, analysis_result):
        """Every number in the LLM report must exist in the source data or calculations"""
        numbers_in_report = extract_numbers(analysis_result.report.markdown)
        valid_numbers = set(analysis_result.all_source_values() + analysis_result.all_calculated_values())
        for number in numbers_in_report:
            assert number in valid_numbers, f"Fabricated number found: {number}"

    def test_bear_case_always_present(self, analysis_result):
        assert "## Bear Case" in analysis_result.report.markdown

    def test_data_not_available_for_missing(self, analysis_with_gaps):
        assert "Data Not Available" in analysis_with_gaps.report.markdown
```

---

## Frontend Testing (Next.js / React)

### Component Tests

```typescript
describe("ForensicScoreCard", () => {
  it("renders score in correct zone color", () => {
    render(<ForensicScoreCard score={-2.45} zone="safe" title="M-SCORE" interpretation="UNLIKELY MANIPULATOR" />);
    expect(screen.getByText("-2.45")).toHaveClass("text-bull");
  });

  it("shows 'Data Not Available' when score is null", () => {
    render(<ForensicScoreCard score={null} zone={null} title="M-SCORE" interpretation="" />);
    expect(screen.getByText("Data Not Available")).toBeInTheDocument();
  });

  it("expands component breakdown on click", async () => {
    render(<ForensicScoreCard {...propsWithComponents} />);
    await userEvent.click(screen.getByText("Component Breakdown"));
    expect(screen.getByText("DSRI")).toBeVisible();
  });
});

describe("CitationTooltip", () => {
  it("shows source on hover", async () => {
    render(<CitationTooltip citation={mockCitation}><span>$60.9B</span></CitationTooltip>);
    await userEvent.hover(screen.getByText("$60.9B"));
    expect(await screen.findByText("Net Receivables")).toBeVisible();
    expect(screen.getByText("Balance Sheet, FY 2024")).toBeVisible();
  });

  it("is keyboard accessible", async () => {
    render(<CitationTooltip citation={mockCitation}><button>$60.9B</button></CitationTooltip>);
    await userEvent.tab();
    expect(screen.getByText("Net Receivables")).toBeVisible();
  });
});

describe("PortfolioTable", () => {
  it("sorts by P&L when column header clicked", async () => {
    render(<PortfolioTable holdings={mockHoldings} />);
    await userEvent.click(screen.getByText("P&L (%)"));
    const rows = screen.getAllByRole("row");
    // Verify descending order
  });

  it("colors P&L green for gains, red for losses", () => {
    render(<PortfolioTable holdings={holdingsWithMixedPnL} />);
    expect(screen.getByText("+23.46%")).toHaveClass("text-bull");
    expect(screen.getByText("-5.20%")).toHaveClass("text-bear");
  });
});
```

### Accessibility Tests

```typescript
describe("Accessibility", () => {
  it("ForensicScoreCard has no violations", async () => {
    const { container } = render(<ForensicScoreCard {...defaultProps} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("TickerSearchInput has no violations", async () => {
    const { container } = render(<TickerSearchInput onSelect={jest.fn()} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("PortfolioTable has no violations", async () => {
    const { container } = render(<PortfolioTable holdings={mockHoldings} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

---

## End-to-End Tests (Playwright)

```typescript
test("full forensic analysis flow", async ({ page }) => {
  await page.goto("/");
  await page.fill("[data-testid=ticker-search]", "AAPL");
  await page.click("[data-testid=search-result-AAPL]");

  // Wait for analysis to complete
  await expect(page.locator("[data-testid=m-score-card]")).toBeVisible({ timeout: 30000 });
  await expect(page.locator("[data-testid=z-score-card]")).toBeVisible();

  // Verify bear case exists in report
  await expect(page.locator("text=Bear Case")).toBeVisible();

  // Verify citation tooltip works
  await page.hover("[data-testid=cited-value]");
  await expect(page.locator("[data-testid=citation-tooltip]")).toBeVisible();
});

test("portfolio management flow", async ({ page }) => {
  await page.goto("/portfolio");
  await page.click("text=Add Holding");
  await page.fill("[name=ticker]", "AAPL");
  await page.fill("[name=shares]", "100");
  await page.fill("[name=costBasis]", "150.25");
  await page.click("button[type=submit]");

  await expect(page.locator("text=AAPL")).toBeVisible();
  await expect(page.locator("text=100")).toBeVisible();
});
```

---

## CI Integration

**Run on every commit:**
- Python: `pytest --cov` (unit + integration, exclude E2E)
- Frontend: `vitest run` (component + unit)
- Linting: `ruff check` (Python), `eslint` (TypeScript)
- Type checking: `mypy` (Python), `tsc --noEmit` (TypeScript)

**Run on PR:**
- All above + coverage report
- Accessibility audit

**Run before release:**
- E2E tests (Playwright)
- Performance audit (Lighthouse)

---

**Created:** 2026-01-30
**Last Updated:** 2026-01-30
**Owner:** @Compliance_Officer
