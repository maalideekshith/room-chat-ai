import { useState } from "react"
import { Icon } from "./Icon"

interface PasswordFieldProps {
  id: string
  label: string
  value: string
  onChange(value: string): void
  autoComplete: "current-password" | "new-password"
  error?: string
  helper?: string
}

export function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  error,
  helper,
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false)
  const descriptionId = error ? `${id}-error` : helper ? `${id}-help` : undefined

  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>{label}</label>
      <div className={`password-input${error ? " field--invalid" : ""}`}>
        <input
          id={id}
          name={id}
          type={visible ? "text" : "password"}
          value={value}
          autoComplete={autoComplete}
          onChange={(event) => onChange(event.currentTarget.value)}
          aria-invalid={Boolean(error)}
          aria-describedby={descriptionId}
          required
        />
        <button
          className="password-input__toggle"
          type="button"
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          aria-pressed={visible}
          onClick={() => setVisible((current) => !current)}
        >
          <Icon name={visible ? "eye-off" : "eye"} />
        </button>
      </div>
      {error && <p className="field__message field__message--error" id={`${id}-error`}>{error}</p>}
      {!error && helper && <p className="field__message" id={`${id}-help`}>{helper}</p>}
    </div>
  )
}
