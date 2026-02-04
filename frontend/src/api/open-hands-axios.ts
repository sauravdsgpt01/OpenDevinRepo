import axios, { AxiosError, AxiosResponse } from "axios";
import { clearLoginData, LOCAL_STORAGE_KEYS } from "#/utils/local-storage";

export const openHands = axios.create({
  baseURL: `${window.location.protocol}//${import.meta.env.VITE_BACKEND_BASE_URL || window?.location.host}`,
});

// Helper function to check if a response contains an email verification error
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const checkForEmailVerificationError = (data: any): boolean => {
  const EMAIL_NOT_VERIFIED = "EmailNotVerifiedError";

  if (typeof data === "string") {
    return data.includes(EMAIL_NOT_VERIFIED);
  }

  if (typeof data === "object" && data !== null) {
    if ("message" in data) {
      const { message } = data;
      if (typeof message === "string") {
        return message.includes(EMAIL_NOT_VERIFIED);
      }
      if (Array.isArray(message)) {
        return message.some(
          (msg) => typeof msg === "string" && msg.includes(EMAIL_NOT_VERIFIED),
        );
      }
    }

    // Search any values in object in case message key is different
    return Object.values(data).some(
      (value) =>
        (typeof value === "string" && value.includes(EMAIL_NOT_VERIFIED)) ||
        (Array.isArray(value) &&
          value.some(
            (v) => typeof v === "string" && v.includes(EMAIL_NOT_VERIFIED),
          )),
    );
  }

  return false;
};

// Set up the global interceptor
openHands.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    // Check if it's a 403 error with the email verification message
    if (
      error.response?.status === 403 &&
      checkForEmailVerificationError(error.response?.data)
    ) {
      if (window.location.pathname !== "/settings/user") {
        window.location.reload();
      }
    }

    // Handle 401 Unauthorized errors - session has expired
    // Clear login data so the user is redirected to login page
    if (error.response?.status === 401) {
      const loginMethod = localStorage.getItem(LOCAL_STORAGE_KEYS.LOGIN_METHOD);
      if (loginMethod) {
        // Clear the stored login method - this will trigger the root-layout
        // to redirect the user to the login page instead of showing the
        // ReauthModal and attempting auto-login (which would fail in a loop)
        clearLoginData();
      }
    }

    // Continue with the error for other error handlers
    return Promise.reject(error);
  },
);
