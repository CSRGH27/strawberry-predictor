from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from .prediction_service import generate_predictions
import logging

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_predictions():
    """
    Fonction exécutée par le cron
    """
    try:
        logger.info("🔄 Démarrage génération prédictions...")
        generate_predictions(days=7)
        logger.info("✅ Prédictions générées avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération : {e}")
        import traceback
        traceback.print_exc()

def start_scheduler():
    """
    Démarre le scheduler pour exécuter les prédictions 5×/jour
    """
    scheduler = BlockingScheduler()
    
    # Ajouter le job : 5 fois par jour à 6h, 10h, 14h, 18h, 22h
    scheduler.add_job(
        run_predictions,
        trigger=CronTrigger(hour='6,10,14,18,22', minute=0),
        id='predictions_job',
        name='Génération prédictions',
        replace_existing=True
    )
    
    logger.info("🕐 Scheduler démarré - Prédictions à 6h, 10h, 14h, 18h, 22h")
    logger.info("⏰ Prochaine exécution : " + str(scheduler.get_jobs()[0].next_run_time))
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Scheduler arrêté")

if __name__ == "__main__":
    start_scheduler()
