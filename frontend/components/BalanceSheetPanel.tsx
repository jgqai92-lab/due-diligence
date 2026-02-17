"use client";

import type { FinancialStatement } from "@/types/analysis";
import FinancialStatementTable from "./FinancialStatementTable";

interface BalanceSheetPanelProps {
  statement: FinancialStatement;
}

export default function BalanceSheetPanel({
  statement,
}: BalanceSheetPanelProps) {
  return (
    <FinancialStatementTable
      statement={statement}
      title="Balance Sheet"
    />
  );
}
