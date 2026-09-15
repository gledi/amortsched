import * as React from "react";
import { CalendarIcon } from "lucide-react";

import { Calendar } from "@/components/ui/calendar";
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from "@/components/ui/input-group";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { fromDateValue, toDateValue } from "@/lib/date-value";

type DatePickerProps = Omit<React.ComponentProps<"input">, "onChange" | "type" | "value"> & {
  value: string;
  onValueChange: (value: string) => void;
};

function DatePicker({ value, onValueChange, disabled, ...props }: DatePickerProps) {
  const [open, setOpen] = React.useState(false);
  const [month, setMonth] = React.useState<Date | undefined>(() => fromDateValue(value));
  const selected = fromDateValue(value);

  return (
    <InputGroup>
      <InputGroupInput
        {...props}
        value={value}
        disabled={disabled}
        inputMode="numeric"
        placeholder="YYYY-MM-DD"
        pattern="\d{4}-\d{2}-\d{2}"
        onChange={(event) => {
          const nextValue = event.target.value;
          const nextDate = fromDateValue(nextValue);

          onValueChange(nextValue);
          if (nextDate) setMonth(nextDate);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true);
          }
        }}
      />
      <InputGroupAddon align="inline-end">
        <Popover
          open={open}
          onOpenChange={(nextOpen) => {
            setOpen(nextOpen);
            if (nextOpen) setMonth(fromDateValue(value));
          }}
        >
          <PopoverTrigger
            render={<InputGroupButton variant="ghost" size="icon-xs" disabled={disabled} aria-label="Choose date" />}
          >
            <CalendarIcon />
          </PopoverTrigger>
          <PopoverContent className="w-auto overflow-hidden p-0" align="end" alignOffset={-8} sideOffset={10}>
            <Calendar
              mode="single"
              selected={selected}
              month={month}
              onMonthChange={setMonth}
              onSelect={(date) => {
                onValueChange(toDateValue(date));
                setMonth(date);
                setOpen(false);
              }}
            />
          </PopoverContent>
        </Popover>
      </InputGroupAddon>
    </InputGroup>
  );
}

export { DatePicker };
