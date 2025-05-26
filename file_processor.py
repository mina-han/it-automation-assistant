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
            # CSV 파일 처리 - 데이터베이스 정보 등을 표 형식으로 정리
            try:
                import pandas as pd
                from io import StringIO
                
                # 다양한 인코딩으로 시도
                for encoding in ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']:
                    try:
                        content = uploaded_file.getvalue().decode(encoding)
                        df = pd.read_csv(StringIO(content))
                        break
                    except:
                        continue
                else:
                    # 모든 인코딩 실패 시 기본 처리
                    content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
                    df = pd.read_csv(StringIO(content))
                
                # 데이터베이스 정보 표 형식으로 정리
                formatted_text = f"=== 데이터베이스 정보 목록 ===\n"
                formatted_text += f"총 {len(df)}개의 데이터베이스 정보\n\n"
                
                # 컬럼 정보
                columns = df.columns.tolist()
                formatted_text += f"컬럼 목록: {', '.join(columns)}\n\n"
                
                # 표 헤더
                formatted_text += "| " + " | ".join(columns) + " |\n"
                formatted_text += "|" + "|".join([" --- " for _ in columns]) + "|\n"
                
                # 데이터 행들 (최대 50개까지만 표시)
                for idx, row in df.head(50).iterrows():
                    row_data = []
                    for col in columns:
                        cell_value = str(row[col]) if pd.notna(row[col]) else ""
                        # 셀 길이 제한 (가독성을 위해)
                        if len(cell_value) > 25:
                            cell_value = cell_value[:22] + "..."
                        row_data.append(cell_value)
                    formatted_text += "| " + " | ".join(row_data) + " |\n"
                
                if len(df) > 50:
                    formatted_text += f"\n... (총 {len(df)}개 중 50개만 표시)\n"
                
                # 검색을 위한 상세 데이터 추가
                formatted_text += "\n\n=== 검색 가능한 상세 정보 ===\n\n"
                for idx, row in df.iterrows():
                    formatted_text += f"데이터베이스 {idx + 1}:\n"
                    for col in columns:
                        value = str(row[col]) if pd.notna(row[col]) else "정보없음"
                        formatted_text += f"  {col}: {value}\n"
                    formatted_text += "\n"
                
                return formatted_text, True
                
            except Exception as e:
                return f"CSV 파일 처리 오류: {str(e)}", False
        
        elif file_extension in ['.doc', '.docx']:
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