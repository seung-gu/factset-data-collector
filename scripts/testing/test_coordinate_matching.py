"""좌표 기반 매칭 테스트 스크립트."""

from pathlib import Path
from src.chart_ocr_processor.google_vision_processor import extract_text_with_boxes
from src.chart_ocr_processor.coordinate_matcher import match_quarters_with_numbers


def test_coordinate_matching(image_path: Path):
    """좌표 기반 매칭을 테스트합니다."""
    from src.chart_ocr_processor.coordinate_matcher import (
        find_quarters_at_bottom, 
        find_nearest_number_in_y_range,
        extract_number
    )
    
    print(f"이미지 처리 중: {image_path}")
    
    # OCR 결과 가져오기
    ocr_results = extract_text_with_boxes(image_path)
    print(f"OCR 결과: {len(ocr_results)}개 텍스트 영역")
    
    # 하단의 Q 패턴 찾기
    quarter_boxes = find_quarters_at_bottom(ocr_results, bottom_percent=0.3)
    print(f"\n하단 Q 패턴: {len(quarter_boxes)}개")
    for qb in quarter_boxes[:5]:
        print(f"  - {qb['quarter']}: '{qb['text']}' (y:{qb['top']})")
    
    # 각 Q 박스 주변의 숫자 후보 확인
    print(f"\n=== 숫자 후보 확인 ===")
    for qb in quarter_boxes[:3]:
        print(f"\nQ 박스: {qb['quarter']} (y:{qb['top']}, x:{qb['left']})")
        # 같은 y 범위의 모든 숫자 후보 찾기
        y_tolerance = 50.0  # 더 넓게
        candidates = []
        for box in ocr_results:
            if (box['left'] == qb['left'] and box['top'] == qb['top']):
                continue
            from src.chart_ocr_processor.coordinate_matcher import extract_quarter_pattern, is_same_y_range, calculate_distance
            if extract_quarter_pattern(box['text']) is not None:
                continue
            number = extract_number(box['text'])
            if number is None:
                continue
            if is_same_y_range(qb, box, y_tolerance):
                distance = calculate_distance(qb, box)
                candidates.append({
                    'text': box['text'],
                    'number': number,
                    'x': box['left'],
                    'y': box['top'],
                    'distance': distance
                })
        
        candidates.sort(key=lambda x: x['distance'])
        print(f"  숫자 후보 {len(candidates)}개:")
        for c in candidates[:5]:
            print(f"    - '{c['text']}' = {c['number']} (x:{c['x']}, y:{c['y']}, 거리:{c['distance']:.1f})")
    
    # 좌표 기반 매칭 수행
    matched_results = match_quarters_with_numbers(
        ocr_results,
        bottom_percent=0.3,   # 하단 30%
        y_tolerance=1000.0,   # y 좌표 허용 오차 1000픽셀
        x_tolerance=10.0      # x 좌표 허용 오차 10픽셀
    )
    
    print(f"\n=== 매칭 결과 (총 {len(matched_results)}개) ===")
    for i, result in enumerate(matched_results, 1):
        print(f"{i}. {result['quarter']}: {result['eps']}")
        print(f"   Q 박스: '{result['quarter_box']['text']}' "
              f"(x:{result['quarter_box']['left']}, y:{result['quarter_box']['top']})")
        print(f"   숫자 박스: '{result['number_box']['text']}' "
              f"(x:{result['number_box']['left']}, y:{result['number_box']['top']})")
        print(f"   거리: {result['distance']:.2f}픽셀")
        print()
    
    return matched_results


if __name__ == '__main__':
    test_image = Path('output/estimates/20161209-6.png')
    test_coordinate_matching(test_image)

