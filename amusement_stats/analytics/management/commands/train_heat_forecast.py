from django.core.management.base import BaseCommand

from analytics.services.forecasting import build_forecast_rows, evaluate_baseline_forecasts


class Command(BaseCommand):
    help = "Generate seven-day heat forecasts and baseline evaluation metrics."

    def add_arguments(self, parser):
        parser.add_argument("--model", default="baseline", choices=["baseline", "all", "prophet", "lstm"])
        parser.add_argument("--days", type=int, default=90)
        parser.add_argument("--horizon", type=int, default=7)

    def handle(self, *args, **options):
        model = options["model"]
        days = max(7, min(int(options["days"]), 365))
        horizon = max(1, min(int(options["horizon"]), 14))
        if model in {"prophet", "lstm", "all"}:
            self.stdout.write(self.style.WARNING("Prophet/LSTM are optional enterprise extensions; baseline forecast is generated for runtime stability."))
        payload = build_forecast_rows(days=days, horizon=horizon, model_name="baseline", persist=True)
        evaluations = evaluate_baseline_forecasts(days=days, horizon=horizon)
        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {sum(len(item['forecast']) for item in payload['items'])} forecast rows and {len(evaluations)} evaluations."
            )
        )
