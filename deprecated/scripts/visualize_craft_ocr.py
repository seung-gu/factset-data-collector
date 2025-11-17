"""CRAFT로 감지된 박스에 OCR을 수행하고 텍스트를 표시하는 스크립트."""

from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import easyocr
import pytesseract

from src.chart_ocr_processor.craft_detector import CRAFTDetector


def visualize_craft_with_ocr(image_path: Path, output_path_easyocr: Path, output_path_tesseract: Path):
    """CRAFT로 감지된 박스에 OCR을 수행하고 텍스트를 표시합니다."""
    # 이미지 읽기
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"이미지를 읽을 수 없습니다: {image_path}")
        return
    
    # CRAFT 감지기 초기화
    detector = CRAFTDetector()
    
    # EasyOCR 초기화
    print("EasyOCR 초기화 중...")
    reader = easyocr.Reader(['en'], gpu=False)
    
    # Threshold 설정: text_threshold=0.3, link_threshold=0.15, low_text=0.2
    print("CRAFT 모델로 텍스트 영역 감지 중 (text_threshold=0.3, link_threshold=0.15, low_text=0.2)...")
    text_regions, region_score, affinity_score = detector.detect_text_regions(
        image,
        text_threshold=0.3,
        link_threshold=0.15,
        low_text=0.2
    )
    
    print(f"감지된 텍스트 영역: {len(text_regions)}개")
    
    colors = [
        (0, 255, 0),    # 초록색
        (255, 0, 0),    # 파란색
        (0, 0, 255),    # 빨간색
        (255, 255, 0),  # 청록색
        (255, 0, 255),  # 자홍색
        (0, 255, 255),  # 노란색
    ]
    
    # EasyOCR 결과
    print("\n=== EasyOCR 처리 중 ===")
    img_easyocr = image.copy()
    ocr_results_easyocr = []
    
    for i, region in enumerate(text_regions):
        bbox = region['bbox']
        if isinstance(bbox, list):
            bbox = np.array(bbox)
        pts = np.array(bbox, dtype=np.int32)
        color = colors[i % len(colors)]
        
        # 박스 그리기
        cv2.polylines(img_easyocr, [pts], True, color, 2)
        
        # 박스 영역 크롭
        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        x_min, x_max = max(0, int(min(x_coords)) - 5), min(image.shape[1], int(max(x_coords)) + 5)
        y_min, y_max = max(0, int(min(y_coords)) - 5), min(image.shape[0], int(max(y_coords)) + 5)
        
        cropped = image[y_min:y_max, x_min:x_max]
        
        if cropped.size > 0:
            # EasyOCR로 OCR 수행 (whitelist 없음)
            results = reader.readtext(cropped)
            
            if results:
                text = results[0][1] if results else ''
                confidence = results[0][2] if results else 0.0
            else:
                text = ''
                confidence = 0.0
            
            text = text.strip()
            
            if text:
                ocr_results_easyocr.append({
                    'index': i + 1,
                    'text': text,
                    'bbox': bbox,
                    'x': x_min,
                    'y': y_min
                })
                
                x, y = int(bbox[0][0]), int(bbox[0][1])
                display_text = text[:30] if len(text) > 30 else text
                cv2.putText(img_easyocr, display_text, (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 3)
    
    # Tesseract 결과
    print("\n=== Tesseract 처리 중 ===")
    img_tesseract = image.copy()
    ocr_results_tesseract = []
    
    for i, region in enumerate(text_regions):
        bbox = region['bbox']
        if isinstance(bbox, list):
            bbox = np.array(bbox)
        pts = np.array(bbox, dtype=np.int32)
        color = colors[i % len(colors)]
        
        # 박스 그리기
        cv2.polylines(img_tesseract, [pts], True, color, 2)
        
        # 박스 영역 크롭
        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        x_min, x_max = max(0, int(min(x_coords)) - 5), min(image.shape[1], int(max(x_coords)) + 5)
        y_min, y_max = max(0, int(min(y_coords)) - 5), min(image.shape[0], int(max(y_coords)) + 5)
        
        cropped = image[y_min:y_max, x_min:x_max]
        
        if cropped.size > 0:
            # Tesseract로 OCR 수행 (whitelist 없음)
            gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            pil_image = Image.fromarray(gray)
            text = pytesseract.image_to_string(pil_image, config='--psm 8')
            text = text.strip()
            
            if text:
                ocr_results_tesseract.append({
                    'index': i + 1,
                    'text': text,
                    'bbox': bbox,
                    'x': x_min,
                    'y': y_min
                })
                
                x, y = int(bbox[0][0]), int(bbox[0][1])
                display_text = text[:30] if len(text) > 30 else text
                cv2.putText(img_tesseract, display_text, (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 3)
    
    # 저장
    cv2.imwrite(str(output_path_easyocr), img_easyocr)
    print(f"\nEasyOCR 시각화 결과를 {output_path_easyocr}에 저장했습니다.")
    
    cv2.imwrite(str(output_path_tesseract), img_tesseract)
    print(f"Tesseract 시각화 결과를 {output_path_tesseract}에 저장했습니다.")
    
    # EasyOCR 결과 출력
    print(f"\n=== EasyOCR 결과 (총 {len(ocr_results_easyocr)}개) ===")
    for result in ocr_results_easyocr[:30]:
        print(f"{result['index']:3d}. '{result['text']}' (x:{result['x']}, y:{result['y']})")
    
    if len(ocr_results_easyocr) > 30:
        print(f"... 외 {len(ocr_results_easyocr) - 30}개 더")
    
    # Tesseract 결과 출력
    print(f"\n=== Tesseract 결과 (총 {len(ocr_results_tesseract)}개) ===")
    for result in ocr_results_tesseract[:30]:
        print(f"{result['index']:3d}. '{result['text']}' (x:{result['x']}, y:{result['y']})")
    
    if len(ocr_results_tesseract) > 30:
        print(f"... 외 {len(ocr_results_tesseract) - 30}개 더")


if __name__ == '__main__':
    test_image = Path('output/estimates/20161209-6.png')
    output_path_easyocr = Path('output/preprocessing_test/20161209-6_craft_ocr_easyocr.png')
    output_path_tesseract = Path('output/preprocessing_test/20161209-6_craft_ocr_tesseract.png')
    
    visualize_craft_with_ocr(test_image, output_path_easyocr, output_path_tesseract)

