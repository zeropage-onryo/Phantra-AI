#!/bin/bash
# Affiliate program: a REAL Stripe test-mode run on your Mac. Nothing here
# touches live Stripe or your live database: it uses sk_test keys and your
# local DATABASE_URL. Read it first; it is short.
#
#   1. Put a TEST key in the environment:   export STRIPE_SECRET_KEY=sk_test_...
#   2. ./affiliate-testmode.command
#
# What it does: creates the 20%-off-once coupon in TEST mode, runs the API,
# forwards test webhooks with `stripe listen`, and tells you the 5 clicks.
cd "$(dirname "$0")" || exit 1

case "$STRIPE_SECRET_KEY" in
  sk_test_*) ;;
  *) echo "STRIPE_SECRET_KEY must be an sk_test_ key. Refusing to run against live."; exit 1;;
esac
command -v stripe >/dev/null || { echo "Install the Stripe CLI first: brew install stripe/stripe-cli/stripe"; exit 1; }

# 1. the buyer coupon, test mode (safe to re-run: reuses it if it exists)
if ! stripe coupons retrieve affiliate-buyer-20 --api-key "$STRIPE_SECRET_KEY" >/dev/null 2>&1; then
  stripe coupons create --id affiliate-buyer-20 --percent-off 20 --duration once \
    --name "Referral: 20% off first month" --api-key "$STRIPE_SECRET_KEY" >/dev/null
fi
export STRIPE_AFFILIATE_COUPON=affiliate-buyer-20

# 2. webhook secret for this session
export STRIPE_WEBHOOK_SECRET="$(stripe listen --print-secret --api-key "$STRIPE_SECRET_KEY")"

# 3. an approved partner to refer from (idempotent: approve is a no-op if already approved)
echo
echo "Make a partner first (once): sign in to the studio as yourself, open /affiliates, apply,"
echo "then run:   venv/bin/python -m src.affiliates approve <your-slug>"
echo "Your link will be   http://localhost:3000/?ref=<code>"
echo
echo "Then, in a PRIVATE window: open that link, sign up as a NEW account, buy Standard monthly"
echo "with card 4242 4242 4242 4242. Checkout should show 20% off the first month."
echo "When it finishes, in another terminal:   venv/bin/python -m src.affiliates report"
echo "You should see 1 signup, 1 paying, held = 20%-off price x 25%."
echo "Starter pays on the amount actually paid: \$15 x 0.80 = \$12.00 -> \$3.00 held."
echo

stripe listen --forward-to localhost:8000/billing/webhook --api-key "$STRIPE_SECRET_KEY" &
LISTEN=$!
trap 'kill $LISTEN 2>/dev/null' EXIT
echo "Starting the API (Ctrl-C stops everything)..."
venv/bin/uvicorn app.main:app --port 8000
