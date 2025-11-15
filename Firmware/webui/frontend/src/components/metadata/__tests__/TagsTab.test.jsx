import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import TagsTab from '../TagsTab';

describe('TagsTab', () => {
  describe('User Tags Rendering', () => {
    it('renders user tags as badge pills', () => {
      const data = {
        user_tags: ['moth', 'nocturnal'],
      };

      render(<TagsTab data={data} />);

      const mothTag = screen.getByText('moth');
      const nocturnalTag = screen.getByText('nocturnal');

      expect(mothTag).toBeInTheDocument();
      expect(nocturnalTag).toBeInTheDocument();

      // Check badge styling
      expect(mothTag).toHaveClass('bg-blue-100');
      expect(mothTag).toHaveClass('rounded-full');
    });

    it('renders multiple tags correctly', () => {
      const data = {
        user_tags: ['lepidoptera', 'large', 'fuzzy', 'green'],
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('lepidoptera')).toBeInTheDocument();
      expect(screen.getByText('large')).toBeInTheDocument();
      expect(screen.getByText('fuzzy')).toBeInTheDocument();
      expect(screen.getByText('green')).toBeInTheDocument();
    });

    it('shows empty state when tags array is empty', () => {
      const data = {
        user_tags: [],
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('No tags added yet (Tagging coming in Phase 3)')).toBeInTheDocument();
    });

    it('shows empty state when tags is undefined', () => {
      const data = {
        species: 'Unknown moth',
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('No tags added yet (Tagging coming in Phase 3)')).toBeInTheDocument();
    });
  });

  describe('Species Field', () => {
    it('displays species identification', () => {
      const data = {
        species: 'Luna Moth (Actias luna)',
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('Species')).toBeInTheDocument();
      expect(screen.getByText('Luna Moth (Actias luna)')).toBeInTheDocument();
    });

    it('shows N/A for missing species', () => {
      const data = {
        user_tags: ['moth'],
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('Species')).toBeInTheDocument();
      // Multiple N/A values expected (species and notes)
      expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
    });

    it('treats empty string species as N/A', () => {
      const data = {
        species: '',
      };

      render(<TagsTab data={data} />);

      // Multiple N/A values expected (species and notes)
      expect(screen.getAllByText('N/A')).toHaveLength(2);
    });
  });

  describe('Notes Field', () => {
    it('displays notes field with multiline text', () => {
      const data = {
        notes: 'Found near porch light.\nLarge wingspan, approximately 10cm.\nSluggish movement.',
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('Notes')).toBeInTheDocument();
      expect(screen.getByText(/Found near porch light/)).toBeInTheDocument();
    });

    it('preserves whitespace in notes', () => {
      const data = {
        notes: 'Line 1\nLine 2\n\nLine 4',
      };

      render(<TagsTab data={data} />);

      const notesElement = screen.getByText(/Line 1/);
      expect(notesElement).toHaveClass('whitespace-pre-wrap');
    });

    it('shows N/A for missing notes', () => {
      const data = {
        species: 'Unknown',
      };

      render(<TagsTab data={data} />);

      const notesLabel = screen.getByText('Notes');
      const notesContainer = notesLabel.closest('div').parentElement;
      expect(notesContainer).toHaveTextContent('N/A');
    });

    it('treats empty string notes as N/A', () => {
      const data = {
        notes: '',
      };

      render(<TagsTab data={data} />);

      expect(screen.getAllByText('N/A')).toHaveLength(2); // species and notes
    });
  });

  describe('Read-Only Indicator', () => {
    it('shows read-only indicator', () => {
      const data = {
        user_tags: ['moth'],
        species: 'Unknown',
        notes: 'Test note',
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText(/Read-only/)).toBeInTheDocument();
    });

    it('read-only text is italicized', () => {
      const data = {
        user_tags: ['test'],
      };

      render(<TagsTab data={data} />);

      const readOnlyElement = screen.getByText(/Read-only/);
      expect(readOnlyElement).toHaveClass('italic');
    });
  });

  describe('Null Data Handling', () => {
    it('handles null data', () => {
      render(<TagsTab data={null} />);

      expect(screen.getByText('No tags data available')).toBeInTheDocument();
    });

    it('handles undefined data', () => {
      render(<TagsTab />);

      expect(screen.getByText('No tags data available')).toBeInTheDocument();
    });
  });

  describe('Partial Data Scenarios', () => {
    it('handles only tags provided', () => {
      const data = {
        user_tags: ['moth', 'insect'],
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('moth')).toBeInTheDocument();
      expect(screen.getByText('insect')).toBeInTheDocument();
      expect(screen.getAllByText('N/A')).toHaveLength(2); // species, notes
    });

    it('handles only species provided', () => {
      const data = {
        species: 'Cecropia Moth',
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('Cecropia Moth')).toBeInTheDocument();
      expect(screen.getByText('No tags added yet (Tagging coming in Phase 3)')).toBeInTheDocument();
    });

    it('handles only notes provided', () => {
      const data = {
        notes: 'Interesting specimen',
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('Interesting specimen')).toBeInTheDocument();
      expect(screen.getByText('No tags added yet (Tagging coming in Phase 3)')).toBeInTheDocument();
    });
  });

  describe('Section Header', () => {
    it('renders section header', () => {
      const data = {
        user_tags: ['test'],
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('Tags & Annotations')).toBeInTheDocument();
    });
  });

  describe('Complete Data Scenarios', () => {
    it('renders all fields when all data provided', () => {
      const data = {
        user_tags: ['moth', 'large', 'green'],
        species: 'Luna Moth (Actias luna)',
        notes: 'Beautiful specimen.\nFound at 2:30 AM.',
      };

      render(<TagsTab data={data} />);

      expect(screen.getByText('moth')).toBeInTheDocument();
      expect(screen.getByText('large')).toBeInTheDocument();
      expect(screen.getByText('green')).toBeInTheDocument();
      expect(screen.getByText('Luna Moth (Actias luna)')).toBeInTheDocument();
      expect(screen.getByText(/Beautiful specimen/)).toBeInTheDocument();
    });
  });

  describe('Tag Badge Styling', () => {
    it('tag badges have proper styling', () => {
      const data = {
        user_tags: ['moth'],
      };

      render(<TagsTab data={data} />);

      const tag = screen.getByText('moth');
      expect(tag).toHaveClass('bg-blue-100');
      expect(tag).toHaveClass('rounded-full');
      expect(tag).toHaveClass('px-2');
      expect(tag).toHaveClass('py-1');
    });
  });
});
