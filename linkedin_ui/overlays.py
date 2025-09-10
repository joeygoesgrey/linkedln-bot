"""
Overlay dismissal and popover handling.

Why:
    LinkedIn often shows chat bubbles, toasts, and modals that intercept clicks.
    Centralize safe dismissal to reduce flakiness.

When:
    Before clicking important controls (start post, Post button, etc.).

How:
    Conservative JS and targeted selectors that avoid closing the composer.
"""

import time
import logging
from selenium.webdriver.common.by import By

import config


class OverlayMixin:
    def dismiss_overlays(self, preserve_share_modal=False):
        """
        Dismiss overlays that can block interactions (chat, toasts, drafts, etc.).
        """
        try:
            self._dismiss_global_search_overlay()
        except Exception:
            pass

        # Chat overlay
        try:
            chat_overlay_close_button = self.driver.find_element(
                By.XPATH,
                "//button[contains(@class, 'msg-overlay-bubble-header__control--close')]",
            )
            chat_overlay_close_button.click()
            logging.info("Closed chat overlay.")
        except Exception:
            logging.info("No chat overlay to close.")

        # Notification toast
        try:
            toast_close_button = self.driver.find_element(
                By.XPATH, "//button[contains(@class, 'artdeco-toast-item__dismiss')]"
            )
            toast_close_button.click()
            logging.info("Closed notification toast.")
        except Exception:
            logging.info("No notification toast to close.")

        if not preserve_share_modal:
            # Save draft dialog
            try:
                save_draft_dialog = self.driver.find_element(
                    By.XPATH, "//div[contains(@class, 'save-draft-dialog')]"
                )
                discard_button = save_draft_dialog.find_element(
                    By.XPATH, ".//button[contains(@class, 'artdeco-button--secondary')]"
                )
                discard_button.click()
                logging.info("Dismissed save draft dialog.")
                self.random_delay(1, 2)
            except Exception:
                logging.info("No save draft dialog to dismiss.")

            # Unsaved detour dialog
            try:
                unsaved_dialog = self.driver.find_element(
                    By.XPATH, "//div[contains(@class, 'unsaved-detour-dialog')]"
                )
                dismiss_button = unsaved_dialog.find_element(
                    By.XPATH, ".//button[contains(@class, 'artdeco-button--secondary')]"
                )
                dismiss_button.click()
                logging.info("Dismissed unsaved detour dialog.")
                self.random_delay(1, 2)
            except Exception:
                logging.info("No unsaved detour dialog to dismiss.")

        # Generic modal dismiss (avoid composer)
        if not preserve_share_modal:
            try:
                modal_close_button = self.driver.find_element(
                    By.XPATH, "//button[contains(@class, 'artdeco-modal__dismiss')]"
                )
                try:
                    modal_close_button.find_element(
                        By.XPATH, "ancestor::div[contains(@class,'share-box-modal')]"
                    )
                    logging.info("Detected share composer modal; preserving it.")
                    raise Exception("Preserve share composer")
                except Exception:
                    pass
                modal_close_button.click()
                logging.info("Closed a modal dialog using dismiss button.")
                self.random_delay(1, 2)
            except Exception:
                logging.info("No modal dialog dismiss button found or preserved.")

        # Special handling for draft modal while composer is present
        try:
            composer_present = False
            for root in [
                "//div[@role='dialog' and contains(@class, 'share-creation-state')]",
                "//div[@role='dialog' and contains(@class, 'share-box-modal')]",
                "//div[contains(@class, 'share-box-modal')]",
            ]:
                try:
                    self.driver.find_element(By.XPATH, root)
                    composer_present = True
                    break
                except Exception:
                    continue
            if composer_present:
                try:
                    draft_modal = self.driver.find_element(
                        By.XPATH,
                        "//div[contains(@class,'artdeco-modal') and (.//button[normalize-space(.)='Save as draft'] or .//button[normalize-space(.)='Discard'])]",
                    )
                    try:
                        close_btn = draft_modal.find_element(
                            By.XPATH,
                            ".//button[contains(@class,'artdeco-modal__dismiss') or @aria-label='Dismiss' or @aria-label='Close']",
                        )
                        close_btn.click()
                        logging.info("Closed 'Save as draft' modal to resume composing.")
                        self.random_delay(0.5, 1.0)
                    except Exception:
                        logging.info(
                            "Could not locate dismiss button on 'Save as draft' modal; leaving it alone."
                        )
                except Exception:
                    pass
        except Exception:
            pass

        # Unexpected overlay with close button
        if not preserve_share_modal:
            try:
                close_button = self.driver.find_element(
                    By.XPATH,
                    "//button[@aria-label='Close' or @aria-label='Dismiss' or contains(@class, 'close-btn')]",
                )
                close_button.click()
                logging.info("Closed an unexpected overlay.")
                self.random_delay(1, 2)
            except Exception:
                logging.info("No unexpected overlay to close.")

        # Remove modal backdrops via JS, conservative
        if not preserve_share_modal:
            try:
                self.driver.execute_script(
                    """
                    var backdrops = document.querySelectorAll('.artdeco-modal-overlay, .artdeco-modal__overlay');
                    backdrops.forEach(function(backdrop) { backdrop.remove(); });
                    document.body.style.overflow = 'auto';
                    """
                )
                logging.info("Attempted to remove modal backdrops with JavaScript.")
            except Exception as e:
                logging.info(f"JavaScript modal removal unsuccessful: {e}")

    def _dismiss_global_search_overlay(self):
        """
        Hide the global header search typeahead if visible (non-destructive).
        """
        try:
            js_probe = """
                const sels = [
                  '.search-typeahead-v2',
                  '.search-typeahead-v2__hit',
                  '.search-global-typeahead',
                  'div[id*="global-nav"] .typeahead',
                ];
                let visible = 0;
                for (const s of sels) {
                  document.querySelectorAll(s).forEach(n => {
                    const shown = !!(n && (n.offsetWidth || n.offsetHeight || n.getClientRects().length));
                    if (shown) visible++;
                  });
                }
                return visible;
            """
            visible_count = int(self.driver.execute_script(js_probe) or 0)
        except Exception:
            visible_count = 0
        if visible_count <= 0:
            return
        try:
            js_hide = """
                const sels = [
                  '.search-typeahead-v2',
                  '.search-typeahead-v2__hit',
                  '.search-global-typeahead',
                  'div[id*="global-nav"] .typeahead',
                ];
                for (const s of sels) {
                  document.querySelectorAll(s).forEach(n => {
                    n.style.display = 'none';
                    n.style.visibility = 'hidden';
                    n.style.pointerEvents = 'none';
                  });
                }
                return true;
            """
            self.driver.execute_script(js_hide)
        except Exception:
            pass

