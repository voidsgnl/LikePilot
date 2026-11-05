"""
LikePilot Human Behavior Simulation Module
Implements Bezier curve mouse movements, variable scroll speeds, and human-like inertia
to bypass advanced bot detection systems.
"""
import random
import time
import math
from typing import Tuple, List

class HumanBehavior:
    """Simulates human mouse movements and interactions."""

    @staticmethod
    def generate_bezier_path(start: Tuple[int, int], end: Tuple[int, int], steps: int = 20) -> List[Tuple[int, int]]:
        """
        Generate a list of coordinates following a cubic Bezier curve.
        Mimics the natural arc of a human hand moving a mouse.
        """
        # Control points for the curve (randomized for uniqueness)
        # Offset control points to create a natural arc
        offset_x = random.randint(-100, 100)
        offset_y = random.randint(-100, 100)
        
        cp1 = (start[0] + offset_x, start[1] + offset_y)
        cp2 = (end[0] - offset_x, end[1] - offset_y)
        
        path = []
        for i in range(steps + 1):
            t = i / steps
            t_ = 1 - t
            
            # Cubic Bezier formula
            x = (t_**3 * start[0]) + (3 * t_**2 * t * cp1[0]) + (3 * t_ * t**2 * cp2[0]) + (t**3 * end[0])
            y = (t_**3 * start[1]) + (3 * t_**2 * t * cp1[1]) + (3 * t_ * t**2 * cp2[1]) + (t**3 * end[1])
            
            path.append((int(x), int(y)))
        
        return path

    @staticmethod
    def move_mouse_smooth(driver, start_pos: Tuple[int, int], end_pos: Tuple[int, int], duration: float = 1.5):
        """
        Move the mouse from start to end using a Bezier curve with variable speed.
        Speed accelerates at start and decelerates at end (ease-in-out).
        """
        from selenium.webdriver.common.action_chains import ActionChains
        
        path = HumanBehavior.generate_bezier_path(start_pos, end_pos)
        total_steps = len(path)
        
        # Calculate delays with ease-in-out effect
        # Faster in the middle, slower at start and end
        base_delay = duration / total_steps
        
        for i, (x, y) in enumerate(path):
            try:
                action = ActionChains(driver)
                action.move_to_location(x, y)
                action.perform()
                
                # Variable delay calculation (sinusoidal speed profile)
                progress = i / total_steps
                speed_factor = math.sin(progress * math.pi) # 0 -> 1 -> 0
                delay = base_delay * (1.5 - speed_factor) # Slower at ends
                
                time.sleep(max(0.01, delay))
            except Exception:
                # Ignore movement errors, continue execution
                continue

    @staticmethod
    def human_scroll(driver, element=None, direction: str = 'down', intensity: str = 'normal'):
        """
        Perform a human-like scroll action.
        Humans don't scroll in perfect linear increments.
        """
        # Scroll parameters based on intensity
        params = {
            'low': {'min_lines': 1, 'max_lines': 3, 'pause_min': 0.1, 'pause_max': 0.3},
            'normal': {'min_lines': 3, 'max_lines': 8, 'pause_min': 0.05, 'pause_max': 0.2},
            'high': {'min_lines': 5, 'max_lines': 15, 'pause_min': 0.02, 'pause_max': 0.1}
        }
        config = params.get(intensity, params['normal'])
        
        total_lines = random.randint(config['min_lines'], config['max_lines'])
        lines_scrolled = 0
        
        while lines_scrolled < total_lines:
            # Random burst size (humans often scroll in small bursts)
            burst = random.randint(1, min(3, total_lines - lines_scrolled))
            
            scroll_amount = burst * 100  # Pixels per line approx
            
            if direction == 'down':
                script = f"window.scrollBy(0, {scroll_amount});"
            else:
                script = f"window.scrollBy(0, -{scroll_amount});"
            
            try:
                if element:
                    driver.execute_script("arguments[0].scrollBy(0, arguments[1]);", element, scroll_amount)
                else:
                    driver.execute_script(script)
            except Exception:
                pass
            
            lines_scrolled += burst
            
            # Random pause between bursts
            if lines_scrolled < total_lines:
                time.sleep(random.uniform(config['pause_min'], config['pause_max']))
        
        # Final settling pause
        time.sleep(random.uniform(0.2, 0.5))

    @staticmethod
    def random_delay(base_seconds: float = 2.0, variance: float = 0.5) -> float:
        """
        Generate a random delay with Gaussian distribution.
        Most delays cluster around the base, with some outliers.
        """
        delay = random.gauss(base_seconds, variance)
        return max(0.5, delay) # Minimum 0.5s to avoid suspicion

    @staticmethod
    def simulate_reading_time(text_length: int, wpm: int = 200) -> float:
        """
        Calculate how long a human would take to read a given text length.
        Adds randomness to simulate skimming or careful reading.
        """
        words = text_length / 5  # Average word length
        base_time = (words / wpm) * 60  # Time in seconds
        
        # Random factor: sometimes people read faster or slower
        factor = random.uniform(0.8, 1.5)
        return base_time * factor

    @staticmethod
    def interact_with_element(driver, element, action: str = 'click'):
        """
        Perform an interaction (click, type) with human-like imperfections.
        Includes slight offset clicks and variable key press durations.
        """
        from selenium.webdriver.common.action_chains import ActionChains
        
        try:
            location = element.location_once_scrolled_into_view
            size = element.size
            
            # Calculate center with slight random offset (humans aren't pixel perfect)
            x_offset = random.randint(-5, 5)
            y_offset = random.randint(-5, 5)
            
            x = location['x'] + (size['width'] / 2) + x_offset
            y = location['y'] + (size['height'] / 2) + y_offset
            
            if action == 'click':
                # Move to element with bezier curve
                current_pos = (0, 0) # Approximate, ideally track last known pos
                HumanBehavior.move_mouse_smooth(driver, current_pos, (x, y), duration=random.uniform(0.5, 1.2))
                
                # Click
                actions = ActionChains(driver)
                actions.click().perform()
                
                # Post-click pause (human reaction time)
                time.sleep(random.uniform(0.1, 0.3))
                
            elif action == 'double_click':
                HumanBehavior.move_mouse_smooth(driver, (0, 0), (x, y), duration=random.uniform(0.5, 1.0))
                actions = ActionChains(driver)
                actions.double_click().perform()
                time.sleep(random.uniform(0.2, 0.4))
                
        except Exception as e:
            # Fallback to standard click if simulation fails
            if action == 'click':
                element.click()

# Helper function for easy import
def get_human_behavior() -> HumanBehavior:
    return HumanBehavior()
