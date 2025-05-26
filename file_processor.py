import streamlit as st
import base64
import io
import re
import csv
import pandas as pd
from typing import Optional, Tuple

def extract_text_from_file(uploaded_file) -> Tuple[str, bool]:
    """
    파일에서 텍스트를 추출합니다.
    Returns: (extracted_text, success)
    """
    try:
        file_extension = uploaded_file.name.lower().split('.')[-1]
        
        if file_extension == 'txt':
            # 텍스트 파일 처리
            content = uploaded_file.read()
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = content.decode('cp949')  # 한글 인코딩
                except UnicodeDecodeError:
                    text = content.decode('latin-1', errors='ignore')
            return text, True
            
        elif file_extension in ['xlsx', 'xls']:
            # Excel 파일 처리 (간단한 방법)
            try:
                import pandas as pd
                df = pd.read_excel(uploaded_file)
                text = df.to_string(index=False)
                return text, True
            except Exception:
                return "Excel 파일 처리 중 오류가 발생했습니다.", False
                
        elif file_extension == 'pdf':
            # PDF 파일 처리 (기본적인 텍스트 추출)
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text if text.strip() else "PDF에서 텍스트를 추출할 수 없습니다.", bool(text.strip())
            except Exception:
                return "PDF 파일 처리를 위해 PyPDF2 라이브러리가 필요합니다.", False
                
        elif file_extension in ['jpg', 'jpeg', 'png']:
            # 이미지 파일 처리 (OCR 없이는 텍스트 추출 불가)
            return "이미지 파일의 텍스트 추출을 위해서는 OCR 라이브러리가 필요합니다. 수동으로 텍스트를 입력해주세요.", False
            
        elif file_extension == '.csv':
            # CSV 파일 처리
            try:
                # 파일 내용을 읽어서 pandas DataFrame으로 변환
                content = uploaded_file.getvalue().decode('utf-8')
                from io import StringIO
                df = pd.read_csv(StringIO(content))
                
                # 표 형식으로 정리된 텍스트 생성
                formatted_text = f"총 {len(df)} 개의 데이터 항목이 있습니다.\n\n"
                formatted_text += f"컬럼 정보: {', '.join(df.columns.tolist())}\n\n"
                
                # 각 행을 구조화된 텍스트로 변환
                for idx, row in df.iterrows():
                    formatted_text += f"=== 데이터 {idx + 1} ===\n"
                    for col in df.columns:
                        formatted_text += f"{col}: {row[col]}\n"
                    formatted_text += "\n"
                
                return formatted_text, True
            except Exception as e:
                try:
                    # 인코딩 문제일 수 있으므로 다른 인코딩으로 시도
                    content = uploaded_file.getvalue().decode('cp949')
                    from io import StringIO
                    df = pd.read_csv(StringIO(content))
                    
                    formatted_text = f"총 {len(df)} 개의 데이터 항목이 있습니다.\n\n"
                    formatted_text += f"컬럼 정보: {', '.join(df.columns.tolist())}\n\n"
                    
                    for idx, row in df.iterrows():
                        formatted_text += f"=== 데이터 {idx + 1} ===\n"
                        for col in df.columns:
                            formatted_text += f"{col}: {row[col]}\n"
                        formatted_text += "\n"
                    
                    return formatted_text, True
                except Exception:
                    return f"CSV 파일 처리 중 오류가 발생했습니다: {str(e)}", False
        
        elif file_extension in ['doc', 'docx']:
            # Word 파일 처리
            try:
                import docx
                doc = docx.Document(uploaded_file)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text, True
            except Exception:
                return "Word 파일 처리를 위해 python-docx 라이브러리가 필요합니다.", False
        else:
            return f"지원하지 않는 파일 형식입니다: {file_extension}", False
            
    except Exception as e:
        return f"파일 처리 중 오류가 발생했습니다: {str(e)}", False

def save_uploaded_file(uploaded_file, save_path: str) -> bool:
    """
    업로드된 파일을 저장합니다.
    """
    try:
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except Exception:
        return False

def get_file_info(uploaded_file) -> dict:
    """
    파일 정보를 반환합니다.
    """
    return {
        "name": uploaded_file.name,
        "size": uploaded_file.size,
        "type": uploaded_file.type
    }