type PlanOfferFields = {
  lender: string | null;
  upfront_fees: number;
};

type PlanOfferFieldsError = {
  error: string;
};

export function parsePlanOfferFields(lender: string, upfrontFees: string): PlanOfferFields | PlanOfferFieldsError {
  const normalizedLender = lender.trim() || null;
  const normalizedFees = upfrontFees.trim();
  const fees = normalizedFees === "" ? 0 : Number(normalizedFees);

  if (!Number.isFinite(fees)) {
    return { error: "Enter valid upfront fees" };
  }

  if (fees < 0) {
    return { error: "Upfront fees must be zero or greater" };
  }

  return { lender: normalizedLender, upfront_fees: fees };
}
