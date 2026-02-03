import { openHands } from "../open-hands-axios";

/**
 * Billing Service API - Handles all billing-related API endpoints
 */
class BillingService {
  /**
   * Create a Stripe checkout session for credit purchase
   * @param amount The amount to charge in dollars
   * @returns The redirect URL for the checkout session
   */
  static async createCheckoutSession(amount: number): Promise<string> {
    const { data } = await openHands.post(
      "/api/billing/create-checkout-session",
      {
        amount,
      },
    );
    return data.redirect_url;
  }

  /**
   * Create a customer setup session for payment method management
   * @returns The redirect URL for the customer setup session
   */
  static async createBillingSessionResponse(): Promise<string> {
    const { data } = await openHands.post(
      "/api/billing/create-customer-setup-session",
    );
    return data.redirect_url;
  }

  /**
   * Get the user's current credit balance
   * @returns The user's credit balance as a string
   */
  static async getBalance(): Promise<string> {
    const { data } = await openHands.get<{ credits: string }>(
      "/api/billing/credits",
    );
    return data.credits;
  }

  /**
   * Get the user's subscription access information
   * @returns The user's subscription access details or null if not available
   */

  /**
   * Create a subscription checkout session for subscribing to a plan
   * @returns The redirect URL for the subscription checkout session
   */

  /**
   * Cancel the user's subscription
   * @returns The response indicating the result of the cancellation request
   */
}

export default BillingService;
