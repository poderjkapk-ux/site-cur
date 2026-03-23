# r_keeper.py
import logging
from typing import List, Dict, Any

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ВИДАЛЕНО: Увесь вміст, пов'язаний з R-Keeper ---
# Замінено на "заглушку", щоб уникнути помилок імпорту в інших файлах.

class RKeeperAPI:
    """
    Заглушка для API R-Keeper. Інтеграцію вимкнено.
    """
    def __init__(self, settings: Any):
        """
        Ініціалізація нічого не робить, оскільки інтеграцію вимкнено.
        """
        # logger.info("Спроба ініціалізації R-Keeper API (інтеграцію вимкнено).")
        pass

    async def send_order(self, order: Any, items: List[Dict[str, Any]]):
        """
        Метод-заглушка для відправки замовлення. 
        Логує попередження і нічого не відправляє.
        """
        logger.warning(
            f"Інтеграцію з R-Keeper вимкнено. "
            f"Замовлення #{order.id if hasattr(order, 'id') else 'N/A'} не було відправлено."
        )
        pass

# Більше жодної логіки R-Keeper в цьому файлі немає.