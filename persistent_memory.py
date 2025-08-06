"""
Database-backed persistent memory implementation for Wizzy Bot
"""
from typing import List, Optional
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from models import ChatHistory, DocumentContext, UserSession, get_database_manager
from datetime import datetime, timedelta
from sqlalchemy import desc
import logging

logger = logging.getLogger(__name__)

class DatabaseChatMessageHistory(BaseChatMessageHistory):
    """Database-backed chat message history implementation"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.db_manager = get_database_manager()
        self._messages = None
        
    @property
    def messages(self) -> List[BaseMessage]:
        """Retrieve messages from database"""
        if self._messages is None:
            self._load_messages()
        return self._messages
    
    def _load_messages(self):
        """Load messages from database (latest 20 messages only)"""
        session = self.db_manager.get_session()
        try:
            # Get only the latest 20 messages for this session
            chat_records = session.query(ChatHistory).filter(
                ChatHistory.session_id == self.session_id
            ).order_by(desc(ChatHistory.timestamp)).limit(20).all()
            
            # Reverse to get chronological order (oldest first)
            chat_records.reverse()
            
            self._messages = []
            for record in chat_records:
                if record.message_type == 'human':
                    message = HumanMessage(content=record.content)
                elif record.message_type == 'ai':
                    message = AIMessage(content=record.content)
                else:
                    continue  # Skip unknown message types
                self._messages.append(message)
                
        except Exception as e:
            logger.error(f"Error loading messages: {e}")
            self._messages = []
        finally:
            self.db_manager.close_session(session)
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the database"""
        session = self.db_manager.get_session()
        try:
            # Auto-cleanup old messages before adding new one
            self._cleanup_old_messages(session)
            
            # Determine message type
            if isinstance(message, HumanMessage):
                message_type = 'human'
            elif isinstance(message, AIMessage):
                message_type = 'ai'
            else:
                message_type = 'system'
            
            # Create chat history record
            chat_record = ChatHistory(
                session_id=self.session_id,
                message_type=message_type,
                content=message.content,
                timestamp=datetime.utcnow()
            )
            
            session.add(chat_record)
            session.commit()
            
            # Update in-memory cache
            if self._messages is not None:
                self._messages.append(message)
                # Keep only latest 20 in memory cache
                if len(self._messages) > 20:
                    self._messages = self._messages[-20:]
                
            # Update user session stats
            self._update_user_session(session)
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            session.rollback()
        finally:
            self.db_manager.close_session(session)
    
    def _cleanup_old_messages(self, session):
        """Auto-delete messages older than 1 day for this session"""
        try:
            # Calculate cutoff time (1 day ago)
            cutoff_time = datetime.utcnow() - timedelta(days=1)
            
            # Delete messages older than 1 day for this session
            deleted_count = session.query(ChatHistory).filter(
                ChatHistory.session_id == self.session_id,
                ChatHistory.timestamp < cutoff_time
            ).delete()
            
            if deleted_count > 0:
                logger.info(f"Auto-deleted {deleted_count} old messages for session {self.session_id}")
            
            session.commit()
        except Exception as e:
            logger.error(f"Error cleaning up old messages: {e}")
    
    def _update_user_session(self, session):
        """Update user session statistics"""
        try:
            user_session = session.query(UserSession).filter(
                UserSession.session_id == self.session_id
            ).first()
            
            if user_session:
                user_session.last_interaction = datetime.utcnow()
                user_session.total_messages += 1
            
            session.commit()
        except Exception as e:
            logger.error(f"Error updating user session: {e}")
    
    def clear(self) -> None:
        """Clear all messages from database"""
        session = self.db_manager.get_session()
        try:
            session.query(ChatHistory).filter(
                ChatHistory.session_id == self.session_id
            ).delete()
            session.commit()
            self._messages = []
        except Exception as e:
            logger.error(f"Error clearing messages: {e}")
            session.rollback()
        finally:
            self.db_manager.close_session(session)

class DatabaseDocumentManager:
    """Manage document contexts in database"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
    
    def store_document(self, session_id: str, filename: str, content: str, 
                      summary: str, file_type: str, file_size: int) -> bool:
        """Store document in database"""
        session = self.db_manager.get_session()
        try:
            # Remove existing document for this session (one document per session)
            session.query(DocumentContext).filter(
                DocumentContext.session_id == session_id
            ).delete()
            
            # Add new document
            doc_context = DocumentContext(
                session_id=session_id,
                filename=filename,
                content=content,
                summary=summary,
                file_type=file_type,
                file_size=file_size,
                uploaded_at=datetime.utcnow()
            )
            
            session.add(doc_context)
            session.commit()
            logger.info(f"Document {filename} stored for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing document: {e}")
            session.rollback()
            return False
        finally:
            self.db_manager.close_session(session)
    
    def get_document(self, session_id: str) -> Optional[dict]:
        """Retrieve document context for session"""
        session = self.db_manager.get_session()
        try:
            doc_context = session.query(DocumentContext).filter(
                DocumentContext.session_id == session_id
            ).first()
            
            if doc_context:
                return {
                    'filename': doc_context.filename,
                    'content': doc_context.content,
                    'summary': doc_context.summary,
                    'file_type': doc_context.file_type,
                    'file_size': doc_context.file_size,
                    'uploaded_at': doc_context.uploaded_at.isoformat()
                }
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving document: {e}")
            return None
        finally:
            self.db_manager.close_session(session)
    
    def delete_document(self, session_id: str) -> bool:
        """Delete document context for session"""
        session = self.db_manager.get_session()
        try:
            session.query(DocumentContext).filter(
                DocumentContext.session_id == session_id
            ).delete()
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            session.rollback()
            return False
        finally:
            self.db_manager.close_session(session)

class UserSessionManager:
    """Manage user sessions in database"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
    
    def create_or_update_session(self, session_id: str, user_name: str = None):
        """Create or update user session"""
        session = self.db_manager.get_session()
        try:
            user_session = session.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()
            
            if user_session:
                # Update existing session
                user_session.last_interaction = datetime.utcnow()
                if user_name and not user_session.user_name:
                    user_session.user_name = user_name
            else:
                # Create new session
                user_session = UserSession(
                    session_id=session_id,
                    user_name=user_name,
                    first_interaction=datetime.utcnow(),
                    last_interaction=datetime.utcnow(),
                    total_messages=0
                )
                session.add(user_session)
            
            session.commit()
        except Exception as e:
            logger.error(f"Error managing user session: {e}")
            session.rollback()
        finally:
            self.db_manager.close_session(session)


# Global cleanup functions
def cleanup_all_old_messages():
    """Cleanup old messages across all sessions (useful for scheduled cleanup)"""
    try:
        db_manager = get_database_manager()
        session = db_manager.get_session()
        
        # Calculate cutoff time (1 day ago)
        cutoff_time = datetime.utcnow() - timedelta(days=1)
        
        # Delete all messages older than 1 day across all sessions
        deleted_count = session.query(ChatHistory).filter(
            ChatHistory.timestamp < cutoff_time
        ).delete()
        
        session.commit()
        
        if deleted_count > 0:
            logger.info(f"Global cleanup: Deleted {deleted_count} old messages across all sessions")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error in global cleanup: {e}")
        session.rollback()
        return 0
    finally:
        db_manager.close_session(session)


def cleanup_old_documents(days: int = 7):
    """Cleanup old documents (default: 7 days)"""
    try:
        db_manager = get_database_manager()
        session = db_manager.get_session()
        
        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Delete old documents
        deleted_count = session.query(DocumentContext).filter(
            DocumentContext.uploaded_at < cutoff_time
        ).delete()
        
        session.commit()
        
        if deleted_count > 0:
            logger.info(f"Document cleanup: Deleted {deleted_count} old documents older than {days} days")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error in document cleanup: {e}")
        session.rollback()
        return 0
    finally:
        db_manager.close_session(session)
