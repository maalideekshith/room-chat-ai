import { describe, expect, it } from "vitest"
import { validateLogin, validateRegistration } from "./validation"

describe("registration validation", () => {
  const valid = {
    username: "  Alex_Morgan ",
    email: " Alex@Example.com ",
    password: "correct horse battery",
    confirmPassword: "correct horse battery",
  }

  it("accepts normalized usernames and backend-compatible passwords", () => {
    expect(validateRegistration(valid)).toEqual({})
    expect(validateRegistration({
      ...valid,
      password: "  12345678901 ",
      confirmPassword: "  12345678901 ",
    })).toEqual({})
  })

  it("rejects username bounds, invalid characters, blank passwords and mismatches", () => {
    expect(validateRegistration({ ...valid, username: "ab" }).username).toBeTruthy()
    expect(validateRegistration({ ...valid, username: "bad-name" }).username).toBeTruthy()
    expect(validateRegistration({ ...valid, password: "           " }).password).toBeTruthy()
    expect(validateRegistration({ ...valid, password: "short" }).password).toBeTruthy()
    expect(validateRegistration({ ...valid, confirmPassword: "different" }).confirmPassword).toBeTruthy()
  })

  it("counts Unicode code points consistently with the backend", () => {
    const password = "🟢".repeat(12)
    expect(validateRegistration({ ...valid, password, confirmPassword: password })).toEqual({})
    const tooLong = "🟢".repeat(129)
    expect(validateRegistration({ ...valid, password: tooLong, confirmPassword: tooLong }).password).toBeTruthy()
    const nonWhitespaceFormatCharacter = "\ufeff".repeat(12)
    expect(validateRegistration({
      ...valid,
      password: nonWhitespaceFormatCharacter,
      confirmPassword: nonWhitespaceFormatCharacter,
    })).toEqual({})
  })
})

describe("login validation", () => {
  it("does not add the registration minimum to existing passwords", () => {
    expect(validateLogin("alex_m", "x")).toBeNull()
  })

  it("rejects empty identifiers and passwords beyond the backend limit", () => {
    expect(validateLogin(" ", "x")).toBeTruthy()
    expect(validateLogin("alex_m", "x".repeat(129))).toBeTruthy()
  })
})
