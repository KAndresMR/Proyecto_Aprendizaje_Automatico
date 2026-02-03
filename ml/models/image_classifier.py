import cv2
import numpy as np
import joblib
import os
from pathlib import Path

class SIFTEngine:
    def __init__(self, storage_path="sift_data.pkl"):
        self.storage_path = storage_path
        self.sift = cv2.SIFT_create()
        # Storage format: { "product_name": [descriptors_1, descriptors_2, ...] }
        # Or simpler: { "product_name": descriptors } if User implies 1 reference image implies 1 descriptor set
        self.database = {} 
        self.load_database()

    def load_database(self):
        if os.path.exists(self.storage_path):
            try:
                self.database = joblib.load(self.storage_path)
                print(f"Loaded SIFT database with {len(self.database)} products.")
            except Exception as e:
                print(f"Failed to load database: {e}")
                self.database = {}
        else:
            self.database = {}

    def save_database(self):
        joblib.dump(self.database, self.storage_path)
        print("SIFT database saved.")

        # MLflow logging
        try:
            import mlflow
            mlflow.set_experiment("SIFT_Product_Registry")
            with mlflow.start_run():
                mlflow.log_artifact(self.storage_path)
                mlflow.log_metric("product_count", len(self.database))
                print("Logged version to MLflow.")
        except Exception as e:
            print(f"MLflow logging failed: {e}")

    def register_product(self, name, image_bgr, mask=None, contrast_threshold=0.04, edge_threshold=10):
        """
        Compute features for reference image and store them.
        contrast_threshold: The contrast threshold used to filter out weak features.
        edge_threshold: The threshold used to filter out edge-like features.
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        
        # Configure SIFT
        if contrast_threshold != 0.04 or edge_threshold != 10:
            self.sift = cv2.SIFT_create(contrastThreshold=contrast_threshold, edgeThreshold=edge_threshold)
        else:
            # Reset to default if matches default, or just create new one
            self.sift = cv2.SIFT_create()

        keypoints, descriptors = self.sift.detectAndCompute(gray, mask)
        
        if descriptors is None:
            return False, "No features detected in image."
            
        self.database[name] = descriptors
        self.save_database()
        return True, f"Registered '{name}' with {len(keypoints)} features."

    def detect_keypoints_vis(self, image_bgr, mask=None, contrast_threshold=0.04, edge_threshold=10):
        """
        Return image with keypoints drawn for visualization.
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        
        # Temp SIFT with params
        sift_temp = cv2.SIFT_create(contrastThreshold=contrast_threshold, edgeThreshold=edge_threshold)
        
        keypoints = sift_temp.detect(gray, mask)
        
        vis_img = cv2.drawKeypoints(image_bgr, keypoints, None, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        return vis_img, len(keypoints)

    def identify_product(self, query_image_bgr, min_match_count=10):
        """
        Compare query image against all registered products.
        Returns the best match label.
        """
        gray_query = cv2.cvtColor(query_image_bgr, cv2.COLOR_BGR2GRAY)
        kp_q, des_q = self.sift.detectAndCompute(gray_query, None)
        
        if des_q is None:
            return None, 0

        bf = cv2.BFMatcher()
        best_label = None
        max_matches = 0
        
        # Iterate all products
        for name, des_ref in self.database.items():
            if des_ref is None: 
                continue
                
            # KNN Match
            matches = bf.knnMatch(des_ref, des_q, k=2)
            
            # Ratio Test
            good = []
            for m, n in matches:
                if m.distance < 0.75 * n.distance:
                    good.append(m)
            
            if len(good) > max_matches:
                max_matches = len(good)
                best_label = name

        if max_matches >= min_match_count:
            return best_label, max_matches
        else:
            return None, max_matches

# Singleton
_sift_instance = None

def get_sift_engine(storage_path="sift_data.pkl"):
    global _sift_instance
    if _sift_instance is None:
        _sift_instance = SIFTEngine(storage_path)
    return _sift_instance
