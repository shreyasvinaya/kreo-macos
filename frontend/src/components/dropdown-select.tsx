import { useEffect, useId, useMemo, useRef, useState } from "react";

export interface DropdownOption {
  value: string;
  label: string;
  meta?: string;
}

interface DropdownSelectProps {
  ariaLabel: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  options: DropdownOption[];
  placeholderLabel?: string;
  value: string | null;
  variant?: "field" | "pill";
}

export function DropdownSelect({
  ariaLabel,
  disabled = false,
  onChange,
  options,
  placeholderLabel = "Select",
  value,
  variant = "field",
}: DropdownSelectProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const listboxId = useId();
  const selectedOption = useMemo(
    () => options.find((option) => option.value === value) ?? null,
    [options, value],
  );

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    window.addEventListener("mousedown", handlePointerDown);
    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener("mousedown", handlePointerDown);
      window.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  return (
    <div className={`dropdown-select dropdown-select-${variant}`} ref={containerRef}>
      <button
        aria-controls={listboxId}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label={ariaLabel}
        className="dropdown-trigger"
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <span className="dropdown-trigger-copy">
          <strong>{selectedOption?.label ?? placeholderLabel}</strong>
          {selectedOption?.meta ? <small>{selectedOption.meta}</small> : null}
        </span>
        <span aria-hidden="true" className={`dropdown-chevron ${open ? "dropdown-chevron-open" : ""}`}>
          ▾
        </span>
      </button>

      {open ? (
        <div className="dropdown-menu" id={listboxId} role="listbox">
          {options.map((option) => {
            const selected = option.value === value;
            return (
              <button
                aria-selected={selected}
                className={`dropdown-option ${selected ? "dropdown-option-selected" : ""}`}
                key={option.value}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
                role="option"
                type="button"
              >
                <span className="dropdown-option-copy">
                  <strong>{option.label}</strong>
                  {option.meta ? <small>{option.meta}</small> : null}
                </span>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
