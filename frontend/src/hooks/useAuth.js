import { useAuthStore } from '../store/authStore'
import { useNavigate } from 'react-router-dom'

export const useAuth = () => {
  const { user, token, login, logout, isAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return {
    user,
    token,
    isAuthenticated,
    login,
    logout: handleLogout,
  }
}