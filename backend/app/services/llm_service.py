"""LLM服务模块"""

from langchain_openai import ChatOpenAI
from ..config import get_settings

# 全局LLM实例
_llm_instance = None
_langchain_llm_instance = None


def get_langchain_llm() -> ChatOpenAI:
    """
    获取LangChain兼容的LLM实例(单例模式)
    
    Returns:
        ChatOpenAI实例
    """
    global _langchain_llm_instance
    
    if _langchain_llm_instance is None:
        import os
        import certifi
        # 修复 SSL 证书路径问题
        # 如果 SSL_CERT_FILE 为空或指向的文件不存在，使用 certifi 提供的证书
        if "SSL_CERT_FILE" not in os.environ or not os.path.exists(os.environ["SSL_CERT_FILE"]):
            os.environ["SSL_CERT_FILE"] = certifi.where()
            print(f"🔧 设置 SSL_CERT_FILE 为: {os.environ['SSL_CERT_FILE']}")
            
        settings = get_settings()
        
        # 优先从环境变量读取, 否则使用配置文件的默认值
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or settings.openai_api_key
        base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or settings.openai_base_url
        model_name = os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or settings.openai_model
        
        _langchain_llm_instance = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            temperature=0.7
        )
        
        print(f"✅ LangChain LLM服务初始化成功")
        print(f"   模型: {model_name}")
        print(f"   Base URL: {base_url}")
    
    return _langchain_llm_instance


def reset_llm():
    """重置LLM实例(用于测试或重新配置)"""
    global _llm_instance, _langchain_llm_instance
    _llm_instance = None
    _langchain_llm_instance = None

