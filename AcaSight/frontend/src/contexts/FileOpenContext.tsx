import React, { createContext, useContext } from 'react';

interface FileOpenMeta {
  file?: string | File;
  pdfUrl?: string;
  abstract?: string;
  authors?: string;
  year?: number | string;
  journal?: string;
}

interface FileOpenContextType {
  openFile: (name: string, type: 'pdf' | 'md', meta?: FileOpenMeta) => void;
}

const FileOpenContext = createContext<FileOpenContextType>({
  openFile: () => {},
});

export const useFileOpen = () => useContext(FileOpenContext);

export const FileOpenProvider: React.FC<{
  openFile: FileOpenContextType['openFile'];
  children: React.ReactNode;
}> = ({ openFile, children }) => (
  <FileOpenContext.Provider value={{ openFile }}>
    {children}
  </FileOpenContext.Provider>
);