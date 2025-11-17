"""CRAFT (Character Region Awareness for Text detection) 모델을 사용한 텍스트 영역 감지."""

import os
from pathlib import Path
from typing import List, Tuple, Optional
import urllib.request

import cv2
import numpy as np
import torch

# CRAFT 모델 import
from .craft import CRAFT
from . import craft_utils
from . import imgproc


class CRAFTDetector:
    """CRAFT 모델을 사용하여 텍스트 영역을 감지합니다."""
    
    def __init__(self, model_path: Optional[Path] = None, device: str = 'cpu'):
        """CRAFT 감지기 초기화.
        
        Args:
            model_path: CRAFT 모델 가중치 파일 경로 (None이면 자동 다운로드)
            device: 사용할 디바이스 ('cpu' 또는 'cuda')
        """
        self.device = torch.device(device)
        self.model_path = model_path or self._get_default_model_path()
        self.model = None
        self._load_model()
    
    def _get_default_model_path(self) -> Path:
        """기본 모델 경로를 반환합니다."""
        # 프로젝트 루트에 있는 모델 파일 우선 확인
        project_model = Path(__file__).parent.parent.parent / 'craft_mlt_25k.pth'
        if project_model.exists():
            return project_model
        
        # 없으면 홈 디렉토리 확인
        model_dir = Path.home() / '.craft_models'
        model_dir.mkdir(exist_ok=True)
        return model_dir / 'craft_mlt_25k.pth'
    
    def _download_model(self, url: str, save_path: Path):
        """모델을 다운로드합니다."""
        print(f"Downloading CRAFT model from {url}...")
        urllib.request.urlretrieve(url, save_path)
        print(f"Model saved to {save_path}")
    
    def _copy_state_dict(self, state_dict):
        """State dict 복사 (DataParallel 대응)."""
        from collections import OrderedDict
        if list(state_dict.keys())[0].startswith("module"):
            start_idx = 1
        else:
            start_idx = 0
        new_state_dict = OrderedDict()
        for k, v in state_dict.items():
            name = ".".join(k.split(".")[start_idx:])
            new_state_dict[name] = v
        return new_state_dict
    
    def _load_model(self):
        """CRAFT 모델을 로드합니다."""
        # 모델이 없으면 다운로드
        if not self.model_path.exists():
            # 여러 URL 시도
            model_urls = [
                "https://github.com/clovaai/CRAFT-pytorch/releases/download/v1.0/craft_mlt_25k.pth",
                "https://github.com/clovaai/CRAFT-pytorch/releases/download/v1.0/craft_mlt_25k.zip",
            ]
            downloaded = False
            for model_url in model_urls:
                try:
                    self._download_model(model_url, self.model_path)
                    downloaded = True
                    break
                except Exception as e:
                    print(f"Failed to download from {model_url}: {e}")
                    continue
            
            if not downloaded:
                print("Failed to download CRAFT model automatically.")
                print("Please download the model manually:")
                print("1. Go to: https://github.com/clovaai/CRAFT-pytorch")
                print("2. Download craft_mlt_25k.pth from releases")
                print(f"3. Save it to: {self.model_path}")
                raise FileNotFoundError(f"CRAFT model not found at {self.model_path}")
        
        # CRAFT 모델 초기화
        self.model = CRAFT(pretrained=False)
        
        # 가중치 로드
        print(f"Loading CRAFT model from {self.model_path}")
        if self.device.type == 'cuda':
            state_dict = torch.load(str(self.model_path))
        else:
            state_dict = torch.load(str(self.model_path), map_location='cpu')
        
        self.model.load_state_dict(self._copy_state_dict(state_dict))
        self.model.to(self.device)
        self.model.eval()
        print("CRAFT model loaded successfully")
    
    def detect_text_regions(
        self, 
        image: np.ndarray,
        text_threshold: float = 0.2,
        link_threshold: float = 0.2,
        low_text: float = 0.2,
        canvas_size: int = 1280,
        mag_ratio: float = 1.5
    ) -> tuple[List[dict], np.ndarray, np.ndarray]:
        """이미지에서 텍스트 영역을 감지합니다.
        
        Args:
            image: 입력 이미지 (BGR 형식)
            text_threshold: 텍스트 영역 임계값
            link_threshold: 연결 임계값
            low_text: 낮은 텍스트 임계값
            canvas_size: 캔버스 크기
            mag_ratio: 확대 비율
            
        Returns:
            텍스트 영역 정보 리스트. 각 항목은:
            {
                'bbox': [[x1, y1], [x2, y2], [x3, y3], [x4, y4]],  # 4개 점
                'score': confidence_score,
                'area': bounding_box_area
            }
        """
        if self.model is None:
            raise RuntimeError("CRAFT model not loaded")
        
        # 이미지 전처리
        img_resized, target_ratio, size_heatmap = imgproc.resize_aspect_ratio(
            image, canvas_size, interpolation=cv2.INTER_LINEAR, mag_ratio=mag_ratio
        )
        ratio_h = ratio_w = 1 / target_ratio
        
        # 정규화
        x = imgproc.normalizeMeanVariance(img_resized)
        x = torch.from_numpy(x).permute(2, 0, 1)  # [h, w, c] to [c, h, w]
        x = x.unsqueeze(0).to(self.device)  # [c, h, w] to [b, c, h, w]
        
        # Forward pass
        with torch.no_grad():
            y, _ = self.model(x)
        
        # Region Score와 Affinity Score 추출
        score_text = y[0, :, :, 0].cpu().data.numpy()  # Region Score
        score_link = y[0, :, :, 1].cpu().data.numpy()   # Affinity Score
        
        # 박스 추출
        boxes, _ = craft_utils.getDetBoxes(
            score_text, score_link, text_threshold, link_threshold, low_text, poly=False
        )
        
        # 좌표 조정
        boxes = craft_utils.adjustResultCoordinates(boxes, ratio_w, ratio_h)
        
        # 결과 변환
        results = []
        for box in boxes:
            # 박스 면적 계산
            w = np.linalg.norm(box[0] - box[1])
            h = np.linalg.norm(box[1] - box[2])
            area = w * h
            
            # 필터링 완화 (작은 글씨와 큰 글씨 모두 포함)
            if area < 10:  # 매우 작은 노이즈만 제거
                continue
            
            results.append({
                'bbox': box.tolist(),
                'score': 0.8,  # CRAFT 점수는 별도로 계산 가능
                'area': area
            })
        
        # 작은 영역 우선 정렬
        results.sort(key=lambda x: x['area'])
        
        # Region Score와 Affinity Score 맵을 결과에 포함
        return results, score_text, score_link


def detect_text_with_craft(image_path: Path, device: str = 'cpu') -> tuple[List[dict], np.ndarray, np.ndarray]:
    """CRAFT를 사용하여 이미지에서 텍스트 영역을 감지합니다.
    
    Args:
        image_path: 이미지 파일 경로
        device: 사용할 디바이스 ('cpu' 또는 'cuda')
        
    Returns:
        (텍스트 영역 정보 리스트, Region Score 맵, Affinity Score 맵)
    """
    detector = CRAFTDetector(device=device)
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"이미지를 읽을 수 없습니다: {image_path}")
    
    return detector.detect_text_regions(image)

