"use client";

import type { FinancialStatement } from "@/types/analysis";
import FinancialStatementTable from "./FinancialStatementTable";

interface IncomeStatementPanelProps {
  statement: FinancialStatement;
}

export default function IncomeStatementPanel({
  statement,
}: IncomeStatementPanelProps) {
  return (
    <FinancialStatementTable
      statement={statement}
      title="Income Statement"
    />
  );
}
