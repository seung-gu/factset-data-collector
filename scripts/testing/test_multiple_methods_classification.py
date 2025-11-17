"""3가지 방법을 모두 사용한 막대그래프 분류 테스트 스크립트."""

import cv2
from pathlib import Path
from src.chart_ocr_processor.google_vision_processor import extract_text_with_boxes
from src.chart_ocr_processor.coordinate_matcher import match_quarters_with_numbers
from src.chart_ocr_processor.bar_classifier import classify_all_bars


def test_multiple_methods(image_path: Path):
    """3가지 방법을 모두 사용하여 막대그래프를 분류하고 결과를 출력합니다."""
    # 이미지 읽기
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"이미지를 읽을 수 없습니다: {image_path}")
        return
    
    # OCR 및 매칭
    print("OCR 및 매칭 수행 중...")
    ocr_results = extract_text_with_boxes(image_path)
    matched_results = match_quarters_with_numbers(ocr_results)
    print(f"총 {len(matched_results)}개 매칭 완료\n")
    
    # 3가지 방법으로 분류
    print("3가지 방법으로 막대그래프 분류 중...")
    classified_results = classify_all_bars(image, matched_results, use_multiple_methods=True)
    
    # 결과 출력
    print("\n=== 분류 결과 ===\n")
    for result in classified_results:
        quarter = result['quarter']
        eps = result['eps']
        bar_color = result['bar_color']
        confidence = result['bar_confidence']
        votes = result['bar_votes']
        methods = result['bar_methods']
        
        print(f"{quarter}: EPS={eps}, Bar={bar_color} (신뢰도: {confidence})")
        print(f"  투표: dark={votes['dark']}, light={votes['light']}")
        print(f"  방법별 결과:")
        print(f"    - Adaptive Threshold: {methods['adaptive']}")
        print(f"    - Morphology Closing: {methods['closing']}")
        print(f"    - OTSU Inverted: {methods['otsu_inv']}")
        print()
    
    # 통계
    high_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'high')
    medium_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'medium')
    low_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'low')
    
    print(f"\n=== 신뢰도 통계 ===")
    print(f"High (3/3 일치): {high_conf}개")
    print(f"Medium (2/3 일치): {medium_conf}개")
    print(f"Low (1/3 또는 0/3): {low_conf}개")


if __name__ == '__main__':
    test_image = Path('output/estimates/20161209-6.png')
    test_multiple_methods(test_image)

