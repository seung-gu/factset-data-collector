"""막대그래프 분류 결과를 시각화하는 스크립트."""

import cv2
import numpy as np
from pathlib import Path
from src.chart_ocr_processor.google_vision_processor import extract_text_with_boxes
from src.chart_ocr_processor.coordinate_matcher import match_quarters_with_numbers
from src.chart_ocr_processor.bar_classifier import classify_all_bars, get_bar_region_coordinates


def visualize_classification_results(image_path: Path, output_path: Path):
    """막대그래프 분류 결과를 시각화합니다."""
    # 이미지 읽기
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"이미지를 읽을 수 없습니다: {image_path}")
        return
    
    # OCR 및 매칭
    print("OCR 및 매칭 수행 중...")
    ocr_results = extract_text_with_boxes(image_path)
    matched_results = match_quarters_with_numbers(ocr_results)
    print(f"총 {len(matched_results)}개 매칭 완료")
    
    # 막대그래프 분류
    print("막대그래프 분류 중...")
    classified_results = classify_all_bars(image, matched_results, use_multiple_methods=True)
    
    # 결과 이미지 생성
    img_result = image.copy()
    
    # 색상 정의 (BGR 형식)
    Q_BOX_COLOR = (0, 255, 0)  # 초록색 - Q 박스
    DARK_BAR_COLOR = (0, 0, 255)  # 빨간색 - dark 막대 (B=0, G=0, R=255)
    LIGHT_BAR_COLOR = (255, 0, 255)  # 자홍색(Magenta) - light 막대 (B=255, G=0, R=255) - 더 명확하게 구분
    
    # 디버깅: 분류 결과 출력
    print("\n=== 막대그래프 분류 결과 ===")
    for i, result in enumerate(classified_results):
        print(f"{i+1}. {result['quarter']}: {result['bar_color']} (votes: {result['bar_votes']})")
    print()
    
    for result in classified_results:
        q_box = result['quarter_box']
        num_box = result['number_box']
        quarter = result['quarter']
        eps = result['eps']
        bar_color = result['bar_color']
        
        # Q 박스 그리기 (초록색)
        q_left = q_box['left']
        q_top = q_box['top']
        q_right = q_left + q_box['width']
        q_bottom = q_top + q_box['height']
        cv2.rectangle(img_result, (q_left, q_top), (q_right, q_bottom), Q_BOX_COLOR, 2)
        
        # Q 텍스트 표시
        cv2.putText(img_result, quarter, (q_left, q_top - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, Q_BOX_COLOR, 2)
        
        # 숫자 박스 색상 결정 (막대그래프 타입에 따라)
        num_box_color = DARK_BAR_COLOR if bar_color == 'dark' else LIGHT_BAR_COLOR
        
        # 숫자 박스 그리기 (막대그래프 타입에 따라 색상 변경)
        num_left = num_box['left']
        num_top = num_box['top']
        num_right = num_left + num_box['width']
        num_bottom = num_top + num_box['height']
        cv2.rectangle(img_result, (num_left, num_top), (num_right, num_bottom), num_box_color, 2)
        
        # 숫자 텍스트 표시 (막대그래프 타입에 따라 색상 변경)
        eps_text = f"{eps}"
        cv2.putText(img_result, eps_text, (num_left, num_top - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, num_box_color, 2)
    
    # 저장
    cv2.imwrite(str(output_path), img_result)
    print(f"\n시각화 결과를 {output_path}에 저장했습니다.")
    
    # 통계 출력
    dark_count = sum(1 for r in classified_results if r['bar_color'] == 'dark')
    light_count = sum(1 for r in classified_results if r['bar_color'] == 'light')
    high_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'high')
    medium_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'medium')
    low_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'low')
    
    print(f"\n=== 분류 통계 ===")
    print(f"Dark bars: {dark_count}개")
    print(f"Light bars: {light_count}개")
    print(f"High confidence: {high_conf}개")
    print(f"Medium confidence: {medium_conf}개")
    print(f"Low confidence: {low_conf}개")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        image_name = sys.argv[1]
    else:
        image_name = '20161209-6.png'
    
    test_image = Path(f'output/estimates/{image_name}')
    output_path = Path(f'output/preprocessing_test/{image_name.replace(".png", "")}_bar_classification.png')
    
    visualize_classification_results(test_image, output_path)

