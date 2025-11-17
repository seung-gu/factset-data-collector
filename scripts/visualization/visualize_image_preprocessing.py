"""이미지 전처리 기법들을 시각화하는 스크립트."""

import cv2
import numpy as np
from pathlib import Path


def apply_preprocessing_techniques(image_path: Path, output_dir: Path):
    """다양한 전처리 기법을 적용하고 결과를 저장합니다."""
    # 이미지 읽기
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"이미지를 읽을 수 없습니다: {image_path}")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 원본 이미지
    cv2.imwrite(str(output_dir / '00_original.png'), image)
    print("원본 이미지 저장 완료")
    
    # 2. 그레이스케일 변환
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(str(output_dir / '01_grayscale.png'), gray)
    print("그레이스케일 변환 완료")
    
    # 3. OTSU 이진화
    _, otsu_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(str(output_dir / '02_otsu_binary.png'), otsu_binary)
    print(f"OTSU 이진화 완료 (임계값: {_})")
    
    # 4. OTSU 이진화 (반전)
    _, otsu_binary_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    cv2.imwrite(str(output_dir / '03_otsu_binary_inv.png'), otsu_binary_inv)
    print("OTSU 이진화 (반전) 완료")
    
    # 5. 적응형 임계값 (Adaptive Threshold)
    adaptive_thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    cv2.imwrite(str(output_dir / '04_adaptive_threshold.png'), adaptive_thresh)
    print("적응형 임계값 완료")
    
    # 6. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_gray = clahe.apply(gray)
    cv2.imwrite(str(output_dir / '05_clahe.png'), clahe_gray)
    print("CLAHE 완료")
    
    # 7. 히스토그램 평활화
    hist_eq = cv2.equalizeHist(gray)
    cv2.imwrite(str(output_dir / '06_histogram_equalization.png'), hist_eq)
    print("히스토그램 평활화 완료")
    
    # 8. 가우시안 블러
    gaussian_blur = cv2.GaussianBlur(gray, (5, 5), 0)
    cv2.imwrite(str(output_dir / '07_gaussian_blur.png'), gaussian_blur)
    print("가우시안 블러 완료")
    
    # 9. 노이즈 제거 (Non-local Means Denoising)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    cv2.imwrite(str(output_dir / '08_denoised.png'), denoised)
    print("노이즈 제거 완료")
    
    # 10. 모폴로지 연산 (Closing)
    kernel = np.ones((3, 3), np.uint8)
    closing = cv2.morphologyEx(otsu_binary, cv2.MORPH_CLOSE, kernel)
    cv2.imwrite(str(output_dir / '09_morphology_closing.png'), closing)
    print("모폴로지 연산 (Closing) 완료")
    
    # 11. 모폴로지 연산 (Opening)
    opening = cv2.morphologyEx(otsu_binary, cv2.MORPH_OPEN, kernel)
    cv2.imwrite(str(output_dir / '10_morphology_opening.png'), opening)
    print("모폴로지 연산 (Opening) 완료")
    
    # 12. CLAHE + OTSU
    clahe_otsu = clahe.apply(gray)
    _, clahe_otsu_binary = cv2.threshold(clahe_otsu, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(str(output_dir / '11_clahe_otsu.png'), clahe_otsu_binary)
    print("CLAHE + OTSU 완료")
    
    # 13. 노이즈 제거 + OTSU
    denoised_otsu = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    _, denoised_otsu_binary = cv2.threshold(denoised_otsu, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(str(output_dir / '12_denoised_otsu.png'), denoised_otsu_binary)
    print("노이즈 제거 + OTSU 완료")
    
    # 14. 히스토그램 평활화 + OTSU
    hist_eq_otsu = cv2.equalizeHist(gray)
    _, hist_eq_otsu_binary = cv2.threshold(hist_eq_otsu, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(str(output_dir / '13_hist_eq_otsu.png'), hist_eq_otsu_binary)
    print("히스토그램 평활화 + OTSU 완료")
    
    print(f"\n모든 전처리 결과를 {output_dir}에 저장했습니다.")


if __name__ == '__main__':
    test_image = Path('output/estimates/20161209-6.png')
    output_dir = Path('output/preprocessing_test/image_preprocessing')
    
    apply_preprocessing_techniques(test_image, output_dir)

