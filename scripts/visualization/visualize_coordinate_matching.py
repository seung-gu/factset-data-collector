"""좌표 기반 매칭 결과를 시각화하는 스크립트."""

import cv2
import numpy as np
from pathlib import Path
from src.chart_ocr_processor.google_vision_processor import extract_text_with_boxes
from src.chart_ocr_processor.coordinate_matcher import match_quarters_with_numbers


def visualize_matching_results(image_path: Path, output_path: Path):
    """좌표 기반 매칭 결과를 시각화합니다."""
    # 이미지 읽기
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"이미지를 읽을 수 없습니다: {image_path}")
        return
    
    # OCR 결과 가져오기
    ocr_results = extract_text_with_boxes(image_path)
    
    # 좌표 기반 매칭 수행
    matched_results = match_quarters_with_numbers(ocr_results)
    
    # 결과 이미지 생성
    img_result = image.copy()
    
    for result in matched_results:
        q_box = result['quarter_box']
        num_box = result['number_box']
        
        # Q 박스 그리기 (초록색)
        q_left = q_box['left']
        q_top = q_box['top']
        q_right = q_left + q_box['width']
        q_bottom = q_top + q_box['height']
        cv2.rectangle(img_result, (q_left, q_top), (q_right, q_bottom), (0, 255, 0), 2)
        
        # Q 텍스트 표시
        cv2.putText(img_result, result['quarter'], (q_left, q_top - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 숫자 박스 그리기 (빨간색)
        num_left = num_box['left']
        num_top = num_box['top']
        num_right = num_left + num_box['width']
        num_bottom = num_top + num_box['height']
        cv2.rectangle(img_result, (num_left, num_top), (num_right, num_bottom), (0, 0, 255), 2)
        
        # 숫자 텍스트 표시
        cv2.putText(img_result, f"{result['eps']}", (num_left, num_top - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # 연결선 그리기 (노란색)
        q_center_x = q_left + q_box['width'] / 2
        q_center_y = q_top + q_box['height'] / 2
        num_center_x = num_left + num_box['width'] / 2
        num_center_y = num_top + num_box['height'] / 2
        
        cv2.line(img_result, 
                (int(q_center_x), int(q_center_y)),
                (int(num_center_x), int(num_center_y)),
                (0, 255, 255), 2)
    
    # 저장
    cv2.imwrite(str(output_path), img_result)
    print(f"매칭 결과 시각화를 {output_path}에 저장했습니다.")
    print(f"총 {len(matched_results)}개 매칭 완료")


if __name__ == '__main__':
    test_image = Path('output/estimates/20161209-6.png')
    output_path = Path('output/preprocessing_test/20161209-6_coordinate_matching.png')
    
    visualize_matching_results(test_image, output_path)

