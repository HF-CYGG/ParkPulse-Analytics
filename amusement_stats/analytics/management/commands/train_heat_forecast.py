from django.core.management.base import BaseCommand

from analytics.forecasting.pipeline import run_forecast_pipeline


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
        payload = run_forecast_pipeline(model=model, days=days, horizon=horizon, persist=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {sum(len(item['forecast']) for item in payload['items'])} forecast rows with {payload['mode']} mode."
            )
        )
