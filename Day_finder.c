#include <stdio.h>

void getDayOfWeek(int d, int m, int y) {
    // Adjustment for January and February
    if (m < 3) {
        m += 12;
        y--;
    }

    int k = y % 100; // Year of the century
    int j = y / 100; // Zero-based century

    // Zeller's Congruence Formula
    int h = (d + (13 * (m + 1) / 5) + k + (k / 4) + (j / 4) + (5 * j)) % 7;

    // Convert Zeller's output to standard days
    // Zeller's: 0 = Saturday, 1 = Sunday, 2 = Monday...
    const char *days[] = {
        "Saturday", "Sunday", "Monday", "Tuesday", 
        "Wednesday", "Thursday", "Friday"
    };

    printf("The day is: %s\n", days[h]);
}

int main() {
    int day, month, year;

    printf("Enter date (DD MM YYYY): ");
    if (scanf("%d %d %d", &day, &month, &year) != 3) {
        printf("Invalid input.\n");
        return 1;
    }

    getDayOfWeek(day, month, year);

    return 0;
}
