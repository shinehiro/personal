import pyautogui
import cv2
import numpy as np
import time
import keyboard
import sys
import os
import threading
import json
from datetime import datetime
from PIL import ImageGrab, Image, ImageDraw, ImageFont

# =========================
# CONFIGURATION SECTION
# =========================
class Config:
    # Paths and files
    MONSTER_IMAGES_DIR = "monster_templates/"
    CONFIG_FILE = "bot_config.json"
    LOG_FILE = "bot_activity.log"
    
    # Detection settings
    CONFIDENCE_THRESHOLD = 0.7
    USE_GAUSSIAN_BLUR = True
    BLUR_KERNEL_SIZE = (5, 5)
    BLUR_SIGMA = 0
    
    # Action settings
    CLICK_OFFSET_X = 0
    CLICK_OFFSET_Y = 0
    CLICK_DELAY = 0.1
    KEY_SPAM_INTERVAL = 0.05
    KEY_SEQUENCE = ['1', '2']  # Keys to press in sequence
    KEY_PRESSES_PER_DETECT = 10
    
    # Advanced settings
    SCAN_REGION = None  # (x, y, width, height) or None for full screen
    CALIBRATION_MODE = False
    VISUAL_FEEDBACK = True
    ESCAPE_KEY = 'esc'
    PAUSE_KEY = 'f9'
    
    @classmethod
    def load(cls):
        """Load configuration from file if it exists"""
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r') as f:
                    config_data = json.load(f)
                
                # Update class attributes from loaded config
                for key, value in config_data.items():
                    if hasattr(cls, key):
                        setattr(cls, key, value)
                
                print(f"Configuration loaded from {cls.CONFIG_FILE}")
        except Exception as e:
            print(f"Error loading configuration: {e}")
    
    @classmethod
    def save(cls):
        """Save current configuration to file"""
        try:
            # Create a dict of all uppercase attributes
            config_data = {key: getattr(cls, key) for key in dir(cls) 
                          if key.isupper() and not key.startswith('__')}
            
            # Convert non-serializable types (like tuples) to lists
            for key, value in config_data.items():
                if isinstance(value, tuple):
                    config_data[key] = list(value)
            
            with open(cls.CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            print(f"Configuration saved to {cls.CONFIG_FILE}")
        except Exception as e:
            print(f"Error saving configuration: {e}")


# =========================
# UTILITY FUNCTIONS
# =========================
class BotLogger:
    """Logging utility for the bot"""
    @staticmethod
    def log(message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"
        
        print(log_message.strip())
        
        try:
            with open(Config.LOG_FILE, 'a') as f:
                f.write(log_message)
        except Exception as e:
            print(f"Error writing to log file: {e}")


class VisualFeedback:
    """Provides visual feedback on detected monsters"""
    @staticmethod
    def draw_detection(screenshot, detection_result):
        """Draw detection outline and info on a copy of the screenshot"""
        if not Config.VISUAL_FEEDBACK or detection_result is None:
            return
        
        try:
            # Convert numpy array to PIL Image
            img = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img)
            
            # Get detection details
            center_x, center_y = detection_result["position"]
            w, h = detection_result["size"]
            confidence = detection_result["confidence"]
            template = detection_result["template"]
            
            # Calculate rectangle coordinates
            left = center_x - w//2
            top = center_y - h//2
            right = center_x + w//2
            bottom = center_y + h//2
            
            # Calculate click position
            click_x = center_x + Config.CLICK_OFFSET_X
            click_y = center_y + Config.CLICK_OFFSET_Y
            
            # Draw detection rectangle
            draw.rectangle([left, top, right, bottom], outline="red", width=2)
            
            # Draw center point
            draw.ellipse([center_x-5, center_y-5, center_x+5, center_y+5], fill="blue")
            
            # Draw click point
            draw.ellipse([click_x-5, click_y-5, click_x+5, click_y+5], fill="green")
            
            # Draw info text
            info_text = f"Match: {template}\nConf: {confidence:.2f}"
            draw.text((left, top-30), info_text, fill="red")
            
            # Display the image
            img.show()
            
        except Exception as e:
            BotLogger.log(f"Error creating visual feedback: {e}", "ERROR")


# =========================
# MONSTER DETECTION
# =========================
class MonsterDetector:
    """Handles loading templates and detecting monsters"""
    def __init__(self):
        self.templates = []
        self.load_templates()
    
    def load_templates(self):
        """Load all monster image templates from the directory"""
        BotLogger.log(f"Loading monster templates from {Config.MONSTER_IMAGES_DIR}")
        
        try:
            if not os.path.exists(Config.MONSTER_IMAGES_DIR):
                os.makedirs(Config.MONSTER_IMAGES_DIR)
                BotLogger.log(f"Created directory {Config.MONSTER_IMAGES_DIR}. Please add monster images.", "WARNING")
                BotLogger.log("Exiting script. Restart after adding images.", "WARNING")
                sys.exit(0)
                
            image_files = [f for f in os.listdir(Config.MONSTER_IMAGES_DIR) 
                          if f.endswith(('.png', '.jpg', '.jpeg'))]
            
            if not image_files:
                BotLogger.log(f"No image files found in {Config.MONSTER_IMAGES_DIR}", "ERROR")
                sys.exit(1)
                
            for image_file in image_files:
                path = os.path.join(Config.MONSTER_IMAGES_DIR, image_file)
                template = cv2.imread(path, cv2.IMREAD_COLOR)
                if template is not None:
                    self.templates.append({"name": image_file, "template": template})
                    BotLogger.log(f"Loaded template: {image_file}")
                else:
                    BotLogger.log(f"Failed to load template: {image_file}", "ERROR")
                    
            BotLogger.log(f"Loaded {len(self.templates)} monster templates")
            
        except Exception as e:
            BotLogger.log(f"Error loading monster templates: {e}", "ERROR")
            sys.exit(1)
    
    def apply_gaussian_blur(self, image):
        """Apply Gaussian blur to an image"""
        if Config.USE_GAUSSIAN_BLUR:
            kernel_size = tuple(Config.BLUR_KERNEL_SIZE) if isinstance(Config.BLUR_KERNEL_SIZE, list) else Config.BLUR_KERNEL_SIZE
            return cv2.GaussianBlur(image, kernel_size, Config.BLUR_SIGMA)
        return image
    
    def capture_screen(self):
        """Capture the current screen or region"""
        if Config.SCAN_REGION:
            x, y, width, height = Config.SCAN_REGION
            screenshot = ImageGrab.grab(bbox=(x, y, x+width, y+height))
            # Adjust detection coordinates to match full screen
            self.region_offset = (x, y)
        else:
            screenshot = ImageGrab.grab()
            self.region_offset = (0, 0)
            
        return np.array(screenshot)
    
    def detect_monster(self, screen):
        """Detect any monster template in the screen"""
        # Convert to grayscale
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to screen
        screen_gray = self.apply_gaussian_blur(screen_gray)
        
        best_confidence = Config.CONFIDENCE_THRESHOLD
        best_template_name = None
        best_position = None
        best_size = None
        
        for template_data in self.templates:
            template = template_data["template"]
            template_name = template_data["name"]
            
            # Convert template to grayscale
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Apply same Gaussian blur to template for consistency
            template_gray = self.apply_gaussian_blur(template_gray)
            
            h, w = template_gray.shape  # Get template dimensions
            
            # Perform template matching
            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            
            # Find the best match position
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > best_confidence:
                best_confidence = max_val
                center_x = max_loc[0] + w // 2 + self.region_offset[0]
                center_y = max_loc[1] + h // 2 + self.region_offset[1]
                best_position = (center_x, center_y)
                best_template_name = template_name
                best_size = (w, h)
        
        if best_position:
            return {
                "position": best_position, 
                "confidence": best_confidence, 
                "template": best_template_name,
                "size": best_size
            }
        
        return None


# =========================
# ACTION CONTROLLER
# =========================
class ActionController:
    """Handles all mouse and keyboard actions"""
    def __init__(self):
        self.paused = False
        
    def calculate_click_position(self, detection_result):
        """Calculate adjusted click position based on detection and offsets"""
        center_x, center_y = detection_result["position"]
        
        # Calculate the click position with offsets
        click_x = center_x + Config.CLICK_OFFSET_X
        click_y = center_y + Config.CLICK_OFFSET_Y
        
        return (click_x, click_y)
    
    def click_and_spam_keys(self, position):
        """Click on the monster and spam configured keys"""
        if self.paused or Config.CALIBRATION_MODE or not position:
            return
            
        x, y = position
        
        # Move mouse to target location and click
        pyautogui.moveTo(x, y)
        pyautogui.click()
        
        # Spam keys according to configuration
        for _ in range(Config.KEY_PRESSES_PER_DETECT):
            for key in Config.KEY_SEQUENCE:
                pyautogui.press(key)
                time.sleep(Config.KEY_SPAM_INTERVAL)
    
    def toggle_pause(self):
        """Toggle the pause state of the bot"""
        self.paused = not self.paused
        state = "PAUSED" if self.paused else "RESUMED"
        BotLogger.log(f"Bot {state}", "STATUS")
        
    def calibration_mode(self, detection_result):
        """Run calibration to help find the right click spot"""
        if detection_result:
            center_x, center_y = detection_result["position"]
            template = detection_result["template"]
            
            BotLogger.log(f"\nCALIBRATION MODE ACTIVE", "STATUS")
            BotLogger.log(f"Monster detected: {template}", "INFO")
            BotLogger.log(f"Center position: ({center_x}, {center_y})", "INFO")
            BotLogger.log(f"Current offset: X={Config.CLICK_OFFSET_X}, Y={Config.CLICK_OFFSET_Y}", "INFO")
            BotLogger.log(f"Calculated click position: ({center_x + Config.CLICK_OFFSET_X}, {center_y + Config.CLICK_OFFSET_Y})", "INFO")
            BotLogger.log("Move your mouse to where you want to click and press 'c' to capture that position", "INFO")
            
            # Move to the currently calculated position
            pyautogui.moveTo(center_x + Config.CLICK_OFFSET_X, center_y + Config.CLICK_OFFSET_Y)
            
            # Wait for user to press 'c'
            if keyboard.read_key() == 'c':
                # Get current mouse position
                current_x, current_y = pyautogui.position()
                # Calculate new offsets
                new_offset_x = current_x - center_x
                new_offset_y = current_y - center_y
                
                BotLogger.log(f"\nNew recommended offsets:", "INFO")
                BotLogger.log(f"CLICK_OFFSET_X = {new_offset_x}  # Horizontal offset", "INFO")
                BotLogger.log(f"CLICK_OFFSET_Y = {new_offset_y}  # Vertical offset", "INFO")
                
                # Update configuration
                Config.CLICK_OFFSET_X = new_offset_x
                Config.CLICK_OFFSET_Y = new_offset_y
                Config.save()
                
                BotLogger.log("Configuration updated with new offsets", "SUCCESS")
                
                # Give user time to read the message
                time.sleep(3)


# =========================
# MAIN BOT CLASS
# =========================
class RobloxMonsterBot:
    """Main bot class that ties everything together"""
    def __init__(self):
        self.running = False
        self.detector = MonsterDetector()
        self.action_controller = ActionController()
        self.setup_hotkeys()
        
    def setup_hotkeys(self):
        """Setup keyboard hotkeys"""
        keyboard.add_hotkey(Config.ESCAPE_KEY, self.stop)
        keyboard.add_hotkey(Config.PAUSE_KEY, self.action_controller.toggle_pause)
        
    def detect_and_act(self):
        """Main detection and action loop"""
        while self.running:
            try:
                # Skip processing if paused
                if self.action_controller.paused:
                    time.sleep(0.5)
                    continue
                    
                # Capture the current screen
                screen = self.detector.capture_screen()
                
                # Detect any monster orientation
                detection_result = self.detector.detect_monster(screen)
                
                if detection_result:
                    template = detection_result["template"]
                    confidence = detection_result["confidence"]
                    
                    if Config.CALIBRATION_MODE:
                        self.action_controller.calibration_mode(detection_result)
                    else:
                        # Calculate the adjusted click position
                        click_position = self.action_controller.calculate_click_position(detection_result)
                        
                        BotLogger.log(f"Monster detected! Template: {template}, Confidence: {confidence:.2f}")
                        BotLogger.log(f"Clicking at position: {click_position}")
                        
                        # Provide visual feedback if enabled
                        VisualFeedback.draw_detection(screen, detection_result)
                        
                        # Perform the click and key actions
                        self.action_controller.click_and_spam_keys(click_position)
                else:
                    BotLogger.log("No monster detected. Searching...", "DEBUG")
                
                # Add a small delay to prevent high CPU usage
                time.sleep(Config.CLICK_DELAY)
                
            except Exception as e:
                BotLogger.log(f"Error in detection loop: {e}", "ERROR")
                time.sleep(1)
    
    def start(self):
        """Start the bot"""
        self.running = True
        
        BotLogger.log("Roblox Monster Bot starting...", "STATUS")
        BotLogger.log(f"Press {Config.ESCAPE_KEY} to stop, {Config.PAUSE_KEY} to pause/resume", "INFO")
        
        if Config.CALIBRATION_MODE:
            BotLogger.log("CALIBRATION MODE ENABLED - No automated actions will occur", "WARNING")
        
        if Config.USE_GAUSSIAN_BLUR:
            BotLogger.log(f"Gaussian blur enabled with kernel size {Config.BLUR_KERNEL_SIZE}", "INFO")
        
        if Config.SCAN_REGION:
            BotLogger.log(f"Scanning region: {Config.SCAN_REGION}", "INFO")
        
        # Start detection loop in a separate thread
        self.detect_thread = threading.Thread(target=self.detect_and_act)
        self.detect_thread.daemon = True
        self.detect_thread.start()
        
        # Wait for the thread to complete
        try:
            while self.running and self.detect_thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        BotLogger.log("Bot stopped", "STATUS")
        Config.save()
        sys.exit(0)


# =========================
# MAIN ENTRY POINT
# =========================
if __name__ == "__main__":
    # Load configuration
    Config.load()
    
    # Create and start the bot
    bot = RobloxMonsterBot()
    bot.start()
