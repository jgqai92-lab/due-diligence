"use client";

import type { FinancialStatement } from "@/types/analysis";
import FinancialStatementTable from "./FinancialStatementTable";

interface CashFlowPanelProps {
  statement: FinancialStatement;
}

export default function CashFlowPanel({
  statement,
}: CashFlowPanelProps) {
  return (
    <FinancialStatementTable
      statement={statement}
      title="Cash Flow Statement"
    />
  );
}
