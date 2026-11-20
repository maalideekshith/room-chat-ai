const usernamePattern = /^[a-z0-9_]{3,30}$/

function characterCount(value: string): number {
  return Array.from(value).length
}

function isWhitespaceOnly(value: string): boolean {
  return Array.from(value).every((character) => {
    const codePoint = character.codePointAt(0)
    return codePoint !== undefined && (
      (codePoint >= 0x0009 && codePoint <= 0x000d)
      || (codePoint >= 0x001c && codePoint <= 0x0020)
      || codePoint === 0x0085
      || codePoint === 0x00a0
      || codePoint === 0x1680
      || (codePoint >= 0x2000 && codePoint <= 0x200a)
      || codePoint === 0x2028
      || codePoint === 0x2029
      || codePoint === 0x202f
      || codePoint === 0x205f
      || codePoint === 0x3000
    )
  })
}

export interface RegistrationValues {
  username: string
  email: string
  password: string
  confirmPassword: string
}

export type RegistrationErrors = Partial<Record<keyof RegistrationValues, string>>

export function normalizeUsername(value: string): string {
  return value.trim().toLowerCase()
}

export function validateRegistration(values: RegistrationValues): RegistrationErrors {
  const errors: RegistrationErrors = {}
  const username = normalizeUsername(values.username)
  const email = values.email.trim().toLowerCase()

  if (characterCount(username) < 3 || characterCount(username) > 30) {
    errors.username = "Use 3 to 30 characters for your username."
  } else if (!usernamePattern.test(username)) {
    errors.username = "Use lowercase letters, numbers, and underscores only."
  }

  if (!email) errors.email = "Enter your email address."
  else if (characterCount(email) > 320) errors.email = "Email addresses can be up to 320 characters."
  else if (!/^[^\s@]+@[^\s@]+$/.test(email)) errors.email = "Enter a valid email address."

  const passwordLength = characterCount(values.password)
  if (isWhitespaceOnly(values.password)) errors.password = "Password cannot be only spaces."
  else if (passwordLength < 12) errors.password = "Use at least 12 characters."
  else if (passwordLength > 128) errors.password = "Use no more than 128 characters."

  if (values.confirmPassword !== values.password) {
    errors.confirmPassword = "The passwords don’t match."
  }
  return errors
}

export function validateLogin(identifier: string, password: string): string | null {
  const normalized = identifier.trim().toLowerCase()
  if (!normalized) return "Enter your username or email."
  if (characterCount(normalized) > 320) return "Username or email must be 320 characters or fewer."
  if (characterCount(password) > 128) return "Password must be 128 characters or fewer."
  return null
}
