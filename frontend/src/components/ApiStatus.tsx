import { useEffect, useState } from "react"
import { checkServiceHealth } from "../api/auth"

type ServiceState = "checking" | "reachable" | "unavailable"

export function ApiStatus() {
  const [state, setState] = useState<ServiceState>("checking")

  useEffect(() => {
    let mounted = true
    void checkServiceHealth().then((reachable) => {
      if (mounted) setState(reachable ? "reachable" : "unavailable")
    })
    return () => { mounted = false }
  }, [])

  return (
    <span className={`api-status api-status--${state}`} role="status" aria-live="polite">
      <span className="api-status__dot" aria-hidden="true" />
      {state === "checking" && "Checking service"}
      {state === "reachable" && "Service reachable"}
      {state === "unavailable" && "Service unavailable"}
    </span>
  )
}
