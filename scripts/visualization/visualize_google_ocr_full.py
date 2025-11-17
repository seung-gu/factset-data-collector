"""Google Cloud Vision API로 전체 이미지 OCR을 수행하고 텍스트를 표시하는 스크립트."""

from pathlib import Path
import cv2
import numpy as np
import os
from dotenv import load_dotenv

try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False
    print("Warning: google-cloud-vision not available. Install with: uv add google-cloud-vision")

# .env 파일에서 환경변수 로드
load_dotenv()


def visualize_google_ocr_full(image_path: Path, output_path: Path):
    """Google Cloud Vision API로 전체 이미지 OCR을 수행하고 텍스트를 표시합니다."""
    # 이미지 읽기
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"이미지를 읽을 수 없습니다: {image_path}")
        return
    
    if not GOOGLE_VISION_AVAILABLE:
        print("Google Cloud Vision이 설치되지 않았습니다.")
        return
    
    # Google Cloud Vision 초기화
    try:
        # .env 파일에서 키 파일 경로 확인
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not creds_path:
            print("Google Cloud Vision 인증이 필요합니다.")
            print(".env 파일에 다음을 추가하세요:")
            print("  GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-key.json")
            return
        
        # JSON 파일 경로인지 확인
        if not creds_path.endswith('.json') or not Path(creds_path).exists():
            print(f"오류: 키 파일을 찾을 수 없습니다: {creds_path}")
            return
        
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file(creds_path)
        google_client = vision.ImageAnnotatorClient(credentials=credentials)
        print(f"Google Cloud Vision 인증 완료: {creds_path}")
        print("Google Cloud Vision 초기화 완료")
    except Exception as e:
        print(f"Google Cloud Vision 초기화 실패: {e}")
        return
    
    # 전체 이미지에 Google Vision API OCR 수행
    print("\n=== Google Cloud Vision 전체 이미지 OCR 처리 중 ===")
    
    try:
        # 이미지를 bytes로 변환
        _, buffer = cv2.imencode('.jpg', image)
        image_bytes = buffer.tobytes()
        
        # Google Vision API 호출 (전체 이미지)
        vision_image = vision.Image(content=image_bytes)
        response = google_client.text_detection(image=vision_image)
        
        if response.error.message:
            print(f"Google Vision API 오류: {response.error.message}")
            return
        
        # 결과 이미지 생성
        img_result = image.copy()
        ocr_results = []
        
        if response.text_annotations:
            # 첫 번째 결과는 전체 텍스트
            full_text = response.text_annotations[0].description
            print(f"\n전체 인식된 텍스트:\n{full_text[:500]}...")  # 처음 500자만 출력
            
            # 나머지는 개별 단어/텍스트 영역
            for i, annotation in enumerate(response.text_annotations[1:], 1):
                vertices = annotation.bounding_poly.vertices
                
                # 바운딩 박스 좌표 추출
                points = []
                for vertex in vertices:
                    points.append([vertex.x, vertex.y])
                
                if len(points) >= 3:
                    text = annotation.description
                    confidence = getattr(annotation, 'confidence', 1.0)
                    
                    ocr_results.append({
                        'index': i,
                        'text': text,
                        'bbox': points,
                        'confidence': confidence
                    })
                    
                    # 박스 그리기
                    pts = np.array(points, dtype=np.int32)
                    cv2.polylines(img_result, [pts], True, (0, 255, 0), 2)
                    
                    # 텍스트 표시
                    if points:
                        x, y = int(points[0][0]), int(points[0][1])
                        display_text = text[:30] if len(text) > 30 else text
                        cv2.putText(img_result, display_text, (x, y - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 3)
        
        # 저장
        cv2.imwrite(str(output_path), img_result)
        print(f"\nGoogle Cloud Vision 시각화 결과를 {output_path}에 저장했습니다.")
        
        # 결과 출력
        print(f"\n=== Google Cloud Vision 결과 (총 {len(ocr_results)}개) ===")
        for result in ocr_results[:50]:  # 처음 50개만 출력
            print(f"{result['index']:3d}. '{result['text']}' (confidence: {result['confidence']:.2f})")
        
        if len(ocr_results) > 50:
            print(f"... 외 {len(ocr_results) - 50}개 더")
            
    except Exception as e:
        print(f"Google OCR 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_image = Path('output/estimates/20161209-6.png')
    output_path = Path('output/preprocessing_test/20161209-6_google_ocr_full.png')
    
    visualize_google_ocr_full(test_image, output_path)

