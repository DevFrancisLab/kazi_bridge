import api, { authApi } from './api';

export interface RegisterPayload {
  email: string;
  password: string;
  phone_number?: string;
  role: 'CLIENT' | 'FREELANCER';
}

export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  errors?: any;
}

export async function registerUser(payload: RegisterPayload): Promise<ApiResponse> {
  try {
    const response = await authApi.post('/register/', {
      email: payload.email,
      password: payload.password,
      phone_number: payload.phone_number,
      role: payload.role,
    });

    return {
      success: true,
      message: response.data?.message || 'User registered successfully.',
      data: response.data,
    };
  } catch (error: any) {
    if (error.response) {
      return {
        success: false,
        message: error.response.data?.message || 'Registration failed.',
        errors: error.response.data?.errors || error.response.data || null,
      };
    }

    return {
      success: false,
      message: 'Network error. Please check your connection.',
    };
  }
}

export async function signup(payload: RegisterPayload): Promise<ApiResponse> {
  try {
    const response = await authApi.post('/register/', {
      email: payload.email,
      password: payload.password,
      phone_number: payload.phone_number,
      role: payload.role,
    });

    return {
      success: true,
      message: response.data?.message || 'Account created successfully.',
      data: response.data,
    };
  } catch (error: any) {
    if (error.response) {
      return {
        success: false,
        message: error.response.data?.message || 'Signup failed.',
        errors: error.response.data?.errors || error.response.data || null,
      };
    }

    return {
      success: false,
      message: 'Network error. Please check your connection.',
    };
  }
}

export interface LoginPayload {
  email: string;
  password: string;
}

export async function loginUser(payload: LoginPayload): Promise<ApiResponse> {
  try {
    const response = await authApi.post('/login/', {
      email: payload.email,
      password: payload.password,
    });

    return {
      success: true,
      message: response.data?.message || 'Login successful.',
      data: response.data,
    };
  } catch (error: any) {
    if (error.response) {
      return {
        success: false,
        message: error.response.data?.message || 'Login failed.',
        errors: error.response.data?.errors || error.response.data || null,
      };
    }

    return {
      success: false,
      message: 'Network error. Please check your connection.',
    };
  }
}

export async function logoutUser(): Promise<ApiResponse> {
  try {
    await api.post('/logout/');
  } catch (error: any) {
    // optional: ignore backend errors on logout
  }

  localStorage.removeItem('token');
  localStorage.removeItem('role');
  localStorage.removeItem('email');

  return {
    success: true,
    message: 'Logged out successfully.',
  };
}

// Dashboard API functions
export async function getJobs(): Promise<ApiResponse> {
  try {
    const response = await api.get('/jobs/');
    const jobs = Array.isArray(response.data)
      ? response.data
      : Array.isArray(response.data?.results)
      ? response.data.results
      : Array.isArray(response.data?.data)
      ? response.data.data
      : [];

    return {
      success: true,
      data: jobs,
    };
  } catch (error: any) {
    return {
      success: false,
      message: error.response?.data?.message || 'Failed to fetch jobs.',
    };
  }
}

export async function getFreelancers(): Promise<ApiResponse> {
  try {
    const response = await api.get('/freelancers/');
    const freelancers = Array.isArray(response.data)
      ? response.data
      : Array.isArray(response.data?.results)
      ? response.data.results
      : Array.isArray(response.data?.data)
      ? response.data.data
      : [];

    return {
      success: true,
      data: freelancers,
    };
  } catch (error: any) {
    return {
      success: false,
      message: error.response?.data?.message || 'Failed to fetch freelancers.',
    };
  }
}

export async function createJob(payload: { title: string; description: string; budget: number }): Promise<ApiResponse> {
  try {
    const response = await api.post('/jobs/', payload);
    return {
      success: true,
      data: response.data,
      message: 'Job created successfully.',
    };
  } catch (error: any) {
    return {
      success: false,
      message: error.response?.data?.message || 'Failed to create job.',
    };
  }
}

export async function getTasks(): Promise<ApiResponse> {
  try {
    const response = await api.get('/tasks/');
    const tasks = Array.isArray(response.data)
      ? response.data
      : Array.isArray(response.data?.results)
      ? response.data.results
      : Array.isArray(response.data?.data)
      ? response.data.data
      : [];

    return {
      success: true,
      data: tasks,
    };
  } catch (error: any) {
    return {
      success: false,
      message: error.response?.data?.message || 'Failed to fetch tasks.',
    };
  }
}

export async function getEarnings(): Promise<ApiResponse> {
  try {
    const response = await api.get('/earnings/');
    const earnings = Array.isArray(response.data)
      ? response.data
      : Array.isArray(response.data?.results)
      ? response.data.results
      : Array.isArray(response.data?.data)
      ? response.data.data
      : [];

    return {
      success: true,
      data: earnings,
    };
  } catch (error: any) {
    return {
      success: false,
      message: error.response?.data?.message || 'Failed to fetch earnings.',
    };
  }
}
