import { useState } from "react"

export default function Login() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [message, setMessage] = useState("")

  async function handleLogin(e) {
    e.preventDefault()
    setMessage("")

    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    })

    const data = await res.json()
    if (data.error) {
      setMessage(data.error)
    } else {
      // Redirect based on role
      if (data.role === "student") {
        window.location.href = "/student/dashboard"
      } else if (data.role === "teacher") {
        window.location.href = "/teacher/dashboard"
      }
    }
  }

  return (
    <div className="container">
      <h1>Welcome Back</h1>
      <form onSubmit={handleLogin}>
        <label htmlFor="email">Email</label>
        <input 
          type="email" 
          id="email" 
          value={email} 
          onChange={(e) => setEmail(e.target.value)} 
          required 
        />

        <label htmlFor="password">Password</label>
        <input 
          type="password" 
          id="password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
          required 
        />

        <button type="submit">Sign In</button>
      </form>
      <p>
        Don't have an account? <a href="/signup">Sign up</a>
      </p>
      {message && <p style={{ color: "red" }}>{message}</p>}

      <style jsx>{`
        body {
          font-family: Inter, Arial, sans-serif;
          background: linear-gradient(135deg, #eef4ff, #f3f6fb);
          margin: 0;
          padding: 0;
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
        }
        .container {
          max-width: 420px;
          width: 100%;
          background: #fff;
          padding: 40px 32px;
          border-radius: 16px;
          box-shadow: 0 12px 40px rgba(53,106,230,.15);
          text-align: center;
        }
        h1 {
          margin-top: 0;
          margin-bottom: 24px;
          color: #356ae6;
        }
        label {
          display: block;
          margin: 12px 0 6px;
          font-weight: 600;
          color: #172033;
          text-align: left;
        }
        input {
          width: 100%;
          padding: 12px;
          border: 1px solid #d6deea;
          border-radius: 8px;
          font-size: 1rem;
        }
        button {
          margin-top: 20px;
          width: 100%;
          padding: 12px;
          background: #356ae6;
          color: #fff;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          font-size: 1rem;
          transition: background .2s, transform .2s;
        }
        button:hover {
          background: #2858c9;
          transform: translateY(-1px);
        }
        p {
          margin-top: 20px;
          font-size: .95rem;
        }
        a {
          color: #356ae6;
          text-decoration: none;
          font-weight: 600;
        }
        a:hover {
          text-decoration: underline;
        }
      `}</style>
    </div>
  )
}
