import { useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ApiError, register } from "../api/auth"
import { useAuth } from "../auth/AuthContext"
import { AuthLayout } from "../components/AuthLayout"
import { PasswordField } from "../components/PasswordField"
import { normalizeUsername, validateRegistration, type RegistrationErrors, type RegistrationValues } from "./validation"

const initialValues: RegistrationValues = {
  username: "",
  email: "",
  password: "",
  confirmPassword: "",
}

export default function RegisterPage() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [values, setValues] = useState(initialValues)
  const [errors, setErrors] = useState<RegistrationErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function update<K extends keyof RegistrationValues>(key: K, value: RegistrationValues[K]) {
    setValues((current) => ({ ...current, [key]: value }))
    setErrors((current) => ({ ...current, [key]: undefined }))
    setFormError(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)
    const nextErrors = validateRegistration(values)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      const firstInvalid = Object.keys(nextErrors)[0]
      document.getElementById(`register-${firstInvalid}`)?.focus()
      return
    }

    setSubmitting(true)
    try {
      const username = normalizeUsername(values.username)
      await register({
        username,
        email: values.email.trim().toLowerCase(),
        password: values.password,
      })
      try {
        // Registration creates the account but does not create a session; use the existing login flow.
        await signIn({ username_or_email: username, password: values.password })
        navigate("/app", { replace: true })
      } catch {
        navigate("/login", {
          replace: true,
          state: { notice: "Your account is ready. Sign in to continue." },
        })
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setFormError("That username or email is already registered. Try signing in or use different details.")
      } else if (error instanceof ApiError && error.status === 0) {
        setFormError(error.message)
      } else if (error instanceof ApiError && error.status === 422) {
        setFormError("Please check your email address and account details, then try again.")
      } else {
        setFormError("We couldn’t create your account right now. Please try again shortly.")
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <div className="auth-heading">
        <p className="eyebrow">MAKE ROOM FOR BETTER WORK</p>
        <h2>Create your account</h2>
        <p>Start with a secure account for your conversations and shared context.</p>
      </div>

      {formError && <div className="form-alert" role="alert">{formError}</div>}

      <form className="auth-form auth-form--register" onSubmit={handleSubmit} noValidate aria-busy={submitting}>
        <div className="field">
          <label className="field__label" htmlFor="register-username">Username</label>
          <input
            className={`text-input${errors.username ? " field--invalid" : ""}`}
            id="register-username"
            name="username"
            type="text"
            value={values.username}
            onChange={(event) => update("username", event.currentTarget.value)}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            maxLength={64}
            placeholder="e.g. alex_morgan"
            aria-invalid={Boolean(errors.username)}
            aria-describedby={errors.username ? "register-username-error" : "register-username-help"}
            required
          />
          {errors.username
            ? <p className="field__message field__message--error" id="register-username-error">{errors.username}</p>
            : <p className="field__message" id="register-username-help">3–30 characters · letters, numbers, underscores</p>}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="register-email">Email address</label>
          <input
            className={`text-input${errors.email ? " field--invalid" : ""}`}
            id="register-email"
            name="email"
            type="email"
            value={values.email}
            onChange={(event) => update("email", event.currentTarget.value)}
            autoComplete="email"
            autoCapitalize="none"
            maxLength={320}
            placeholder="you@company.com"
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? "register-email-error" : undefined}
            required
          />
          {errors.email && <p className="field__message field__message--error" id="register-email-error">{errors.email}</p>}
        </div>

        <PasswordField
          id="register-password"
          label="Password"
          value={values.password}
          onChange={(value) => update("password", value)}
          autoComplete="new-password"
          error={errors.password}
          helper="12–128 characters. Spaces are allowed when part of your password."
        />

        <PasswordField
          id="register-confirmPassword"
          label="Confirm password"
          value={values.confirmPassword}
          onChange={(value) => update("confirmPassword", value)}
          autoComplete="new-password"
          error={errors.confirmPassword}
        />

        <button className="button button--primary button--full" type="submit" disabled={submitting}>
          {submitting ? <><span className="spinner" aria-hidden="true" /> Creating account…</> : <>Create account <span className="button__arrow">→</span></>}
        </button>
        <p className="form-terms">Your password is securely hashed before it is stored. We’ll never ask you to share it.</p>
      </form>

      <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
    </AuthLayout>
  )
}
