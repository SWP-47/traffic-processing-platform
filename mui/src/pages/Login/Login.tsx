import { useState } from "react";
import type { SubmitEvent } from 'react';
import styles from './Login.module.css';
import auth from "@/services/authentication";
import { useNavigate } from "react-router";
import type { ApiError } from "@/api/errors";

function Login() {
  const navigate = useNavigate();
  const [ submitting, setSubmitting ] = useState<boolean>(false);
  const [ errorMessage, setErrorMessage ] = useState<string>('');

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
    const username = data.get("username") as string;
    const password = data.get("password") as string;

    setSubmitting(true);
    try {
      await auth.login({
        username: username,
        password: password
      });

      navigate("/");
    } catch (e) {
      setErrorMessage((e as ApiError).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <form className={styles.form} onSubmit={handleSubmit}>
        <h1 className={styles.title}>Login</h1>
        <input
          type="text"
          name="username"
          placeholder="Username"
          disabled={submitting}
          required
          className={styles.input}
        />
        <input
          type="password"
          name="password"
          placeholder="Password"
          disabled={submitting}
          required
          className={styles.input}
        />
        <p className={styles.error} style={{
          display: (errorMessage === '' ? 'none' : 'block')
        }}>
          {errorMessage}
        </p>
        <button
          type="submit"
          className={`button ${styles.button}`}
          disabled={submitting}>
            Login
        </button>
      </form>
    </div>
  );
}

export default Login;