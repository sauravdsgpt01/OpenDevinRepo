import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { displayErrorToast } from "#/utils/custom-toast-handlers";

type SubmitOnboardingArgs = {
  selections: Record<string, string>;
};

export const useSubmitOnboarding = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async ({ selections }: SubmitOnboardingArgs) =>
      // TODO: persist user responses
      selections,
    onSuccess: () => {
      navigate("/");
    },
    onError: (error) => {
      displayErrorToast(error.message);
    },
  });
};
