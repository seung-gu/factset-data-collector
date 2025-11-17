"""막대그래프 영역에 다양한 전처리 기법을 적용하고 비교하는 스크립트."""

import cv2
import numpy as np
from pathlib import Path
from src.chart_ocr_processor.google_vision_processor import extract_text_with_boxes
from src.chart_ocr_processor.coordinate_matcher import match_quarters_with_numbers


def apply_preprocessing_to_bar(image: np.ndarray, q_box: dict, num_box: dict) -> dict:
    """막대그래프 영역에 다양한 전처리 기법을 적용합니다."""
    # 막대그래프 영역 정의
    q_center_x = q_box['left'] + q_box['width'] / 2
    num_center_x = num_box['left'] + num_box['width'] / 2
    x_center = int((q_center_x + num_center_x) / 2)
    x_width = 30
    x_min = max(0, int(x_center - x_width / 2))
    x_max = min(image.shape[1], int(x_center + x_width / 2))
    
    y_top = int(num_box['top'] + num_box['height'])
    y_bottom = int(q_box['top'])
    
    # 영역 크롭
    cropped = image[y_top:y_bottom, x_min:x_max]
    
    if cropped.size == 0:
        return {}
    
    # 그레이스케일 변환
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    
    results = {
        'original': cropped,
        'grayscale': gray,
    }
    
    # OTSU 이진화
    _, otsu_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results['otsu'] = otsu_binary
    
    # OTSU 이진화 (반전)
    _, otsu_binary_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    results['otsu_inv'] = otsu_binary_inv
    
    # 적응형 임계값
    adaptive_thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    results['adaptive'] = adaptive_thresh
    
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_gray = clahe.apply(gray)
    results['clahe'] = clahe_gray
    
    # 히스토그램 평활화
    hist_eq = cv2.equalizeHist(gray)
    results['hist_eq'] = hist_eq
    
    # 노이즈 제거
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    results['denoised'] = denoised
    
    # CLAHE + OTSU
    _, clahe_otsu = cv2.threshold(clahe_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results['clahe_otsu'] = clahe_otsu
    
    # 노이즈 제거 + OTSU
    _, denoised_otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results['denoised_otsu'] = denoised_otsu
    
    return results


def visualize_all_bars_preprocessing(image_path: Path, output_dir: Path):
    """모든 막대그래프에 전처리를 적용하고 결과를 저장합니다."""
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"이미지를 읽을 수 없습니다: {image_path}")
        return
    
    ocr_results = extract_text_with_boxes(image_path)
    matched_results = match_quarters_with_numbers(ocr_results)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"총 {len(matched_results)}개의 막대그래프 처리 중...\n")
    
    for result in matched_results:
        quarter = result['quarter'].replace("'", "")
        q_box = result['quarter_box']
        num_box = result['number_box']
        
        preprocessed = apply_preprocessing_to_bar(image, q_box, num_box)
        
        if preprocessed:
            for method, processed_img in preprocessed.items():
                output_path = output_dir / f"bar_{quarter}_{method}.png"
                cv2.imwrite(str(output_path), processed_img)
        
        print(f"{result['quarter']} 처리 완료")
    
    print(f"\n모든 결과를 {output_dir}에 저장했습니다.")


if __name__ == '__main__':
    test_image = Path('output/estimates/20161209-6.png')
    output_dir = Path('output/preprocessing_test/bar_preprocessing')
    
    visualize_all_bars_preprocessing(test_image, output_dir)

