// try-catch with empty catch
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.FileReader;
import java.io.File;
import java.io.IOException;

class Test {
    BufferedReader br;
    public Test(File file) {
        br = new BufferedReader(new FileReader(file));
    }

    public void doTest() {
        String s;
        int i;
        for (i = 0; i < 10; i++)
            System.out.println(i);
        try {
            try {
                br.readLine();
            } catch (IOException e) {
                br.ready();
            }
        } catch (IOException e) {
        }
    }
}
