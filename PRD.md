Product Requirement Document (PRD)
Project: The "Skeptical Analyst" Due Diligence & Portfolio Engine
Version: 1.0 Target User: Strategic Data Scientist & Solo Capital Allocator Core Philosophy: "Trust, but Verify (with Math)."

1. Executive Summary
The "Skeptical Analyst" Engine is a high-fidelity financial dashboard and automated due diligence tool. Unlike generic stock trackers, it applies rigorous forensic accounting (Beneish M-Score, Altman Z-Score) and SaaS-specific metrics (Rule of 40, Magic Number) to validate investment theses. It bridges the gap between analyzing a target asset and managing it within a personal portfolio, effectively automating the workflow of a hedge fund analyst for a solo practitioner.

Forward-Looking Thesis: In 2026, the primary driver of SaaS valuation is no longer "Growth at all costs" but "AI-Native Efficiency." This tool specifically quantifies that variable.

2. User Persona & Problem Statement
User: A Strategic Data Scientist who values "Hard Data" over narrative. Problem:

Information Asymmetry: Retail tools show price; institutional tools show forensic risk.

Hallucinated Analysis: Generic LLMs invent financial figures. We need a "Correctness Engine" that grounds every claim in source data.

Workflow Fragmentation: Due diligence happens in one app (Edgar/Seeking Alpha), portfolio tracking in another (Brokerage), and synthesis in a third (Newsletter/Notes).

3. Functional Requirements
Phase 1: The "Forensic" Due Diligence Engine
Automated "Red Flag" Report:

Input: Ticker Symbol (e.g., $CRWD, $SNOW).

Action: Scrapes 10-K/10-Q financials via API.

Forensic Checks (The "Skeptical" Layer):

Beneish M-Score: Calculates probability of earnings manipulation.

Altman Z-Score: Calculates bankruptcy risk (customized for SaaS liability structures).

SaaS "Quality of Revenue": Calculates Rule of 40 (Growth + FCF Margin) and Magic Number (Net New ARR / S&M Spend).

Output: A Markdown memo citing specific line items that look suspicious (e.g., "DSRI increased by 20% while Sales only grew 5% - potential channel stuffing").

Phase 2: The "Forward-Looking" Valuation Model
AI-Adjusted Efficiency Metric:

Calculates Revenue Per Employee (RPE) and tracks its rate of change.

Thesis: Companies successfully deploying internal AI agents should see RPE skyrocket. This engine flags companies failing to show this efficiency gain.

Sentiment vs. Fundamentals Divergence:

Compares "News Sentiment Score" (from news API) vs. "Fundamental Health Score."

Signal: High Sentiment + Deteriorating Fundamentals = Short Signal.

Phase 3: Portfolio "Watchdog"
Shadow Portfolio:

User inputs holdings and cost basis.

Active Monitoring: The engine re-runs the "Red Flag" report on all portfolio holdings weekly.

Alerting: "Alert: Your holding $PLTR has triggered a Beneish M-Score warning of -1.8."

4. Technical Architecture & Stack
Core Agents (SDE v3.0 Assignment)
@Chief_Architect: Responsible for the data pipeline integrity.

@Backend_Specialist: Python/Node.js based.

@Compliance_Officer: CRITICAL ROLE. This agent acts as the "Skeptic." It explicitly reviews every LLM output against the raw API JSON data to prevent hallucination.

Technology Stack (The "Prosumer" Choice)
Financial Data API: Financial Modeling Prep (FMP).

Why: Best-in-class fundamental data (10-Ks) for the price ($19/mo). Includes a "Stock Screener" endpoint.

Alternative: EODHD (End of Day Historical Data).

Portfolio/Execution API: Alpaca.

Why: Developer-first API for tracking positions and paper-trading execution. Free tier is robust.

LLM Brain: Claude 3.5 Sonnet/Opus (via Anthropic API).

Frontend: Next.js + Tailwind (Neo-Brutalism).

Visual Style: Dense data tables, stark red/green indicators, "Bloomberg Terminal" aesthetic.

5. "Skeptical Analyst" Acceptance Criteria
To ensure this application meets your specific standards for "Correctness":

The "Citation" Rule: Every financial figure displayed in the UI must have a tooltip showing the raw source (e.g., "Source: 10-Q filing, Q3 2025, Line Item: Accounts Receivable").

The "Hallucination" Trap: The System Prompt must include: "If data is missing for a metric (e.g., R&D Spend), explicitly state 'Data Not Available.' DO NOT estimate or extrapolate without clearly labeling it as an estimate."

The "Bear Case" Mandatory: Every generated report must conclude with a "Bear Case" section, regardless of how good the numbers look.

6. Forward-Looking Impact Analysis
Variable: "The Agentic Efficiency Delta"

Hypothesis: By 2027, SaaS companies will bifurcate into "Agent-Native" (high margins, low headcount growth) and "Legacy SaaS" (bloated headcount, linear cost scaling).

Application Impact: This tool tracks the second derivative of Revenue per Employee. It identifies the "Agent-Native" winners before the market fully prices in their margin expansion. This is your "Alpha."

7. Next Steps for @Orchestrator
Initialize SDE Phase 1 (Planning Swarm):

Launch 3x @Chief_Architect agents.

Architect 1: Design the FMP -> Alpaca -> Claude data pipeline.

Architect 2: Define the JSON schema for the "Forensic Report" to ensure the LLM outputs structured data.

Architect 3 (Red Team): Critique the Beneish M-Score applicability for modern SaaS and propose a "Modified SaaS M-Score."

Generate Specs:

Produce spec/03_API_SPEC.md strictly mapping FMP endpoints to our forensic formulas.