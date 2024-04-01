cmake_minimum_required(VERSION 3.10)
project(PyPokerEvalBinding)

# Détecter le système d'exploitation
if(${CMAKE_SYSTEM_NAME} MATCHES "Windows")
    # Chemins personnalisés pour Anaconda si CMake ne trouve pas automatiquement Python sur Windows
    if(EXISTS "$ENV{USERPROFILE}/AppData/Local/Programs/Python/Python311/python.exe")
        set(Python3_EXECUTABLE "$ENV{USERPROFILE}/AppData/Local/Programs/Python/Python311/python.exe")
        set(Python3_LIBRARY "$ENV{USERPROFILE}/AppData/Local/Programs/Python/Python311/libs/python311.lib")
        set(Python3_INCLUDE_DIR "$ENV{USERPROFILE}/AppData/Local/Programs/Python/Python311/include")
    else()
        # Chemins pour Python 3.11 installé par Chocolatey sur Windows
        set(Python3_EXECUTABLE "C:/Python311/python.exe")
        set(Python3_LIBRARY "C:/Python311/libs/python311.lib")
        set(Python3_INCLUDE_DIR "C:/Python311/include")
    endif()
elseif(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    # Chemins pour macOS
    if(EXISTS "$ENV{HOME}/anaconda3/bin/python")
        set(Python3_EXECUTABLE "$ENV{HOME}/anaconda3/bin/python")
        set(Python3_LIBRARY "$ENV{HOME}/anaconda3/lib/libpython3.11.dylib") # Remplacer 3.11 par votre version de Python
        set(Python3_INCLUDE_DIR "$ENV{HOME}/anaconda3/include/python3.11") # Remplacer 3.11 par votre version de Python
    else()
        # Sur macOS, Homebrew installe Python 3.11 dans /usr/local/opt/python@3.11
        set(Python3_EXECUTABLE "/usr/local/opt/python@3.11/bin/python3.11")
        set(Python3_LIBRARY "/usr/local/opt/python@3.11/lib/libpython3.11.dylib")
        set(Python3_INCLUDE_DIR "/usr/local/opt/python@3.11/include/python3.11")
    endif()
elseif(${CMAKE_SYSTEM_NAME} MATCHES "Linux")
    # Chemins pour Linux
    if(EXISTS "$ENV{HOME}/anaconda3/bin/python")
        set(Python3_EXECUTABLE "$ENV{HOME}/anaconda3/bin/python")
        set(Python3_LIBRARY "$ENV{HOME}/anaconda3/lib/libpython3.11.so") # Remplacer 3.11 par votre version de Python
        set(Python3_INCLUDE_DIR "$ENV{HOME}/anaconda3/include/python3.11") # Remplacer 3.11 par votre version de Python
    else()
        # Sur Linux, le PPA deadsnakes permet l'installation de Python 3.11
        set(Python3_EXECUTABLE "/usr/bin/python3.11")
        set(Python3_LIBRARY "/usr/lib/x86_64-linux-gnu/libpython3.11.so")
        set(Python3_INCLUDE_DIR "/usr/include/python3.11")
    endif()
endif()
# Essayez de trouver une installation de Python 3.x
find_package(Python3 COMPONENTS Interpreter Development)
if(Python3_FOUND)
    message(STATUS "Python 3.x trouvé : Version ${Python3_VERSION}, Librairies : ${Python3_LIBRARIES}, Include : ${Python3_INCLUDE_DIRS}")
    include_directories(${Python3_INCLUDE_DIRS})

    # Chemin vers la bibliothèque poker-eval construite, adapté en fonction de l'OS
    if(${CMAKE_SYSTEM_NAME} MATCHES "Windows")
        include_directories("${CMAKE_SOURCE_DIR}/include")
        set(POKER_EVAL_LIB_PATH "${CMAKE_SOURCE_DIR}/poker-eval/build/Debug/poker_lib_static.lib")
    elseif(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
        message(STATUS "CMAKE_SOURCE_DIR is set to ${CMAKE_SOURCE_DIR}")
        include_directories("${CMAKE_SOURCE_DIR}/include")
        set(POKER_EVAL_LIB_PATH "${CMAKE_SOURCE_DIR}/poker-eval/build/libpoker_lib_static.a")
        message(STATUS "POKER_EVAL_LIB_PATH is set to ${POKER_EVAL_LIB_PATH}")
    elseif(${CMAKE_SYSTEM_NAME} MATCHES "Linux")
        include_directories("${CMAKE_SOURCE_DIR}/include")
        set(POKER_EVAL_LIB_PATH "${CMAKE_SOURCE_DIR}/poker-eval/build/libpoker_lib_static.a")
    endif()

    # Incluez les en-têtes de poker-eval si vous les avez
    include_directories("${CMAKE_SOURCE_DIR}/poker-eval/include")

    # Définissez le module Python
    add_library(pypokereval MODULE pypokereval.c)
    target_link_libraries(pypokereval ${Python3_LIBRARIES} ${POKER_EVAL_LIB_PATH})
    set_target_properties(pypokereval PROPERTIES PREFIX "")
else()
    message(WARNING "Python 3.x n'a pas été trouvé, le binding Python ne sera pas construit.")
endif()