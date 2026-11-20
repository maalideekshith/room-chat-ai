import { useState, type FormEvent } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { ApiError } from "../api/auth"
import { useAuth } from "../auth/AuthContext"
import { AuthLayout } from "../components/AuthLayout"
import { Icon } from "../components/Icon"
import { PasswordField } from "../components/PasswordField"
import { normalizeUsername, validateLogin } from "./validation"

interface LocationNotice {
  notice?: string
}

export default function LoginPage() {
  const { signIn, notice: authNotice } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const notice = (location.state as LocationNotice | null)?.notice ?? authNotice
  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const [identifierError, setIdentifierError] = useState<string | undefined>()
  const [passwordError, setPasswordError] = useState<string | undefined>()
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)
    const validationMessage = validateLogin(identifier, password)
    if (validationMessage) {
      if (!identifier.trim() || identifier.trim().length > 320) {
        setIdentifierError(validationMessage)
        setPasswordError(undefined)
        document.getElementById("login-identifier")?.focus()
      } else {
        setPasswordError(validationMessage)
        document.getElementById("login-password")?.focus()
      }
      return
    }
    setIdentifierError(undefined)
    setPasswordError(undefined)
    setSubmitting(true)
    try {
      await signIn({ username_or_email: normalizeUsername(identifier), password })
      navigate("/app", { replace: true })
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFormError("Those sign-in details don’t match an active account.")
      } else if (error instanceof ApiError && error.status === 0) {
        setFormError(error.message)
      } else if (error instanceof ApiError && error.status >= 500) {
        setFormError("Room Chat AI is having trouble right now. Please try again shortly.")
      } else {
        setFormError("We couldn’t sign you in. Check your details and try again.")
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <div className="auth-heading">
        <p className="eyebrow">YOUR SPACE IS WAITING</p>
        <h2>Welcome back</h2>
        <p>Sign in to continue where your team’s thinking left off.</p>
      </div>

      {notice && <div className="notice" role="status"><Icon name="check" />{notice}</div>}
      {formError && <div className="form-alert" role="alert">{formError}</div>}

      <form className="auth-form" onSubmit={handleSubmit} noValidate aria-busy={submitting}>
        <div className="field">
          <label className="field__label" htmlFor="login-identifier">Username or email</label>
          <input
            className={`text-input${identifierError ? " field--invalid" : ""}`}
            id="login-identifier"
            name="username_or_email"
            type="text"
            value={identifier}
            onChange={(event) => {
              setIdentifier(event.currentTarget.value)
              setIdentifierError(undefined)
              setPasswordError(undefined)
            }}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            placeholder="you@company.com"
            aria-invalid={Boolean(identifierError)}
            aria-describedby={identifierError ? "login-identifier-error" : undefined}
            required
          />
          {identifierError && <p className="field__message field__message--error" id="login-identifier-error">{identifierError}</p>}
        </div>

        <PasswordField
          id="login-password"
          label="Password"
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
          error={passwordError}
        />

        <button className="button button--primary button--full" type="submit" disabled={submitting}>
          {submitting ? <><span className="spinner" aria-hidden="true" /> Signing in…</> : <>Sign in <Icon name="arrow" /></>}
        </button>
      </form>

      <p className="auth-switch">New to Room Chat AI? <Link to="/register">Create an account</Link></p>
      <div className="auth-security"><Icon name="lock" /><span>Refresh credentials stay in an HttpOnly cookie and rotate on use.</span></div>
    </AuthLayout>
  )
}
