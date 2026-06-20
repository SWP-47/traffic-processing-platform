import { useState } from "react";
import type { SubmitEvent } from 'react';
import styles from './Login.module.css';

function Login() {
  const [ submitting, setSubmitting ] = useState<boolean>(false);

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();

    const form = event.target;
    const isValid = form.checkValidity();

    const invalidField = form.querySelector(":invalid") as HTMLInputElement;
    invalidField?.focus();

    if (isValid) {
      const data = new FormData(form);
      submit(data);
    }
  }

  const submit = async (data: FormData) => {
    // Test code
    const username = data.get("username");
    const password = data.get("password");
    console.log(username, password);

    setSubmitting(true);
    await new Promise(r => setTimeout(r, 2000));
    setSubmitting(false);
  }

  return (
    <div className={styles.page}>
      <form className={styles.form} onSubmit={handleSubmit}>
        <h1>Login</h1>
        <input
          type="text"
          name="username"
          placeholder="Username"
          disabled={submitting}
          required
        />
        <input
          type="password"
          name="password"
          placeholder="Password"
          disabled={submitting}
          required
        />
        <button
          type="submit"
          className="button"
          disabled={submitting}
        >
          Login
        </button>
      </form>
    </div>
  );
}

export default Login;