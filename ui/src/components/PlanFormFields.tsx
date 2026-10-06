import { NumberField } from "@/components/NumberField";
import { DatePicker } from "@/components/ui/date-picker";
import { Field, FieldDescription, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CURRENCIES } from "@/lib/currency";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import { LOAN_TYPES, mortgageLoanAmount, RATE_APPLICATIONS, type PlanFormValues } from "@/lib/plan-form";
import type { InterestRateApplication, LoanType } from "@/lib/types";

interface PlanFormFieldsProps {
  idPrefix: string;
  values: PlanFormValues;
  onChange: (patch: Partial<PlanFormValues>) => void;
  allowAdjustableRate: boolean;
}

export function PlanFormFields({ idPrefix, values, onChange, allowAdjustableRate }: PlanFormFieldsProps) {
  const id = (name: string) => `${idPrefix}-${name}`;
  const isMortgage = values.loanType === "mortgage";
  const loanAmount = mortgageLoanAmount(values);
  const homePrice = Number(values.homePrice) || 0;
  const downPercent = homePrice > 0 ? (Number(values.downPayment) / homePrice) * 100 : 0;
  const ltv = homePrice > 0 ? (loanAmount / homePrice) * 100 : 0;

  return (
    <FieldGroup>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field className="sm:col-span-2">
          <FieldLabel htmlFor={id("name")}>Plan name</FieldLabel>
          <Input
            id={id("name")}
            placeholder="e.g. Bank Alpha 30-year fixed"
            value={values.name}
            onChange={(event) => onChange({ name: event.target.value })}
            required
          />
        </Field>
        <Field>
          <FieldLabel htmlFor={id("loan-type")}>Loan type</FieldLabel>
          <Select value={values.loanType} onValueChange={(value) => value && onChange({ loanType: value as LoanType })}>
            <SelectTrigger id={id("loan-type")} className="w-full">
              <SelectValue>{LOAN_TYPES.find((option) => option.value === values.loanType)?.label}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {LOAN_TYPES.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>
        <Field>
          <FieldLabel htmlFor={id("currency")}>Currency</FieldLabel>
          <Select value={values.currency} onValueChange={(value) => value && onChange({ currency: value })}>
            <SelectTrigger id={id("currency")} className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {CURRENCIES.map((option) => (
                  <SelectItem key={option.code} value={option.code}>
                    {option.code} · {option.name}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>
        <Field className="sm:col-span-2">
          <FieldLabel htmlFor={id("lender")}>Lender</FieldLabel>
          <Input
            id={id("lender")}
            placeholder="Bank or lender offering this loan (optional)"
            value={values.lender}
            onChange={(event) => onChange({ lender: event.target.value })}
          />
        </Field>
      </div>

      <FieldSet>
        <FieldLegend variant="label">Amount</FieldLegend>
        {isMortgage ? (
          <div className="grid gap-3 sm:grid-cols-3">
            <NumberField
              id={id("home-price")}
              label="Home price"
              value={values.homePrice}
              onChange={(homePrice) => onChange({ homePrice })}
              min="1"
            />
            <NumberField
              id={id("down-payment")}
              label="Down payment"
              value={values.downPayment}
              onChange={(downPayment) => onChange({ downPayment })}
              description={homePrice > 0 ? `${formatPercent(downPercent)} of price` : undefined}
            />
            <Field>
              <FieldLabel>Loan amount</FieldLabel>
              <p className="flex h-8 items-center font-mono text-sm font-semibold">
                {loanAmount > 0 ? formatCurrency(loanAmount, values.currency) : "—"}
              </p>
              <FieldDescription>{homePrice > 0 ? `${formatPercent(ltv)} loan-to-value` : null}</FieldDescription>
            </Field>
          </div>
        ) : (
          <NumberField
            id={id("amount")}
            label="Loan amount"
            value={values.amount}
            onChange={(amount) => onChange({ amount })}
            min="1"
          />
        )}
      </FieldSet>

      <FieldSet>
        <FieldLegend variant="label">Rate &amp; term</FieldLegend>
        <div className="grid gap-3 sm:grid-cols-4">
          <NumberField
            id={id("rate")}
            label="Interest rate (%)"
            value={values.interestRate}
            onChange={(interestRate) => onChange({ interestRate })}
            max="100"
          />
          <NumberField
            id={id("years")}
            label="Years"
            value={values.years}
            onChange={(years) => onChange({ years })}
            step="1"
            max="50"
          />
          <NumberField
            id={id("months")}
            label="Extra months"
            value={values.months}
            onChange={(months) => onChange({ months })}
            step="1"
            max="11"
          />
          <Field>
            <FieldLabel htmlFor={id("start")}>First payment</FieldLabel>
            <DatePicker
              id={id("start")}
              value={values.startDate}
              onValueChange={(startDate) => onChange({ startDate })}
            />
          </Field>
        </div>
        {allowAdjustableRate ? (
          <div className="grid gap-3 sm:grid-cols-3">
            <Field>
              <FieldLabel htmlFor={id("rate-type")}>Rate type</FieldLabel>
              <Select
                value={values.rateType}
                onValueChange={(value) => value && onChange({ rateType: value as PlanFormValues["rateType"] })}
              >
                <SelectTrigger id={id("rate-type")} className="w-full">
                  <SelectValue>{values.rateType === "fixed" ? "Fixed" : "Adjustable (fixed, then resets)"}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="fixed">Fixed</SelectItem>
                    <SelectItem value="adjustable">Adjustable (fixed, then resets)</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>
            {values.rateType === "adjustable" ? (
              <>
                <NumberField
                  id={id("fixed-years")}
                  label="Fixed for (years)"
                  value={values.fixedPeriodYears}
                  onChange={(fixedPeriodYears) => onChange({ fixedPeriodYears })}
                  step="1"
                />
                <NumberField
                  id={id("adjusted-rate")}
                  label="Expected rate after (%)"
                  value={values.adjustedRate}
                  onChange={(adjustedRate) => onChange({ adjustedRate })}
                  max="100"
                />
              </>
            ) : null}
          </div>
        ) : null}
      </FieldSet>

      {isMortgage ? (
        <FieldSet>
          <FieldLegend variant="label">Ownership costs</FieldLegend>
          <FieldDescription>
            Paid with each mortgage payment. PMI counts toward the loan&apos;s cost; tax, insurance, and HOA do not.
          </FieldDescription>
          <div className="grid gap-3 sm:grid-cols-3">
            <NumberField
              id={id("tax")}
              label="Property tax / year"
              value={values.propertyTaxAnnual}
              onChange={(propertyTaxAnnual) => onChange({ propertyTaxAnnual })}
            />
            <NumberField
              id={id("insurance")}
              label="Home insurance / year"
              value={values.insuranceAnnual}
              onChange={(insuranceAnnual) => onChange({ insuranceAnnual })}
            />
            <NumberField
              id={id("hoa")}
              label="HOA dues / month"
              value={values.hoaMonthly}
              onChange={(hoaMonthly) => onChange({ hoaMonthly })}
            />
            <NumberField
              id={id("pmi")}
              label="PMI (% of loan / year)"
              value={values.pmiRate}
              onChange={(pmiRate) => onChange({ pmiRate })}
              max="100"
            />
            <NumberField
              id={id("pmi-ltv")}
              label="PMI ends at LTV (%)"
              value={values.pmiCancelLtv}
              onChange={(pmiCancelLtv) => onChange({ pmiCancelLtv })}
              min="1"
              max="100"
            />
          </div>
        </FieldSet>
      ) : null}

      <FieldSet>
        <FieldLegend variant="label">Fees</FieldLegend>
        <div className="grid gap-3 sm:grid-cols-3">
          <NumberField
            id={id("upfront-fees")}
            label="Upfront fees"
            value={values.upfrontFees}
            onChange={(upfrontFees) => onChange({ upfrontFees })}
            description="Origination, points, closing costs"
          />
          <NumberField
            id={id("early-fixed")}
            label="Prepayment fee (fixed)"
            value={values.earlyFeeFixed}
            onChange={(earlyFeeFixed) => onChange({ earlyFeeFixed })}
          />
          <NumberField
            id={id("early-percent")}
            label="Prepayment fee (%)"
            value={values.earlyFeePercent}
            onChange={(earlyFeePercent) => onChange({ earlyFeePercent })}
            max="100"
          />
        </div>
        <Field>
          <FieldLabel htmlFor={id("application")}>Interest when the rate changes mid-period</FieldLabel>
          <Select
            value={values.application}
            onValueChange={(value) => value && onChange({ application: value as InterestRateApplication })}
          >
            <SelectTrigger id={id("application")} className="w-full">
              <SelectValue>
                {RATE_APPLICATIONS.find((option) => option.value === values.application)?.label}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {RATE_APPLICATIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>
      </FieldSet>
    </FieldGroup>
  );
}
